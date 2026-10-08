import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    MAX_PASSWORD_BYTES,
    REFRESH_TOKEN_TYPE,
    InvalidTokenError,
    TokenExpiredError,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_dummy_password,
    verify_password,
)
from app.models import User
from app.repositories.refresh_token_repository import (
    add_refresh_token,
    delete_refresh_token,
    get_refresh_token_by_jti,
)
from app.repositories.user_repository import add_user, get_user_by_email, get_user_by_id

MIN_PASSWORD_LENGTH = 8
ASCII_LETTER = re.compile(r"[A-Za-z]")
DIGIT = re.compile(r"[0-9]")


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def signup(db: Session, email: str, password: str) -> User:
    if not _is_valid_password(password):
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_PASSWORD",
            "비밀번호는 8자 이상, 72바이트 이하이며 영문과 숫자를 포함해야 합니다",
        )

    normalized_email = email.lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise _email_already_exists()

    user = add_user(db, normalized_email, hash_password(password), _now())
    try:
        db.commit()
    except IntegrityError as exc:
        # 동시 가입으로 unique 제약에 걸린 경우
        db.rollback()
        raise _email_already_exists() from exc
    return user


def login(db: Session, email: str, password: str) -> TokenPair:
    user = get_user_by_email(db, email.lower())
    if user is None:
        verify_dummy_password(password)
        raise _invalid_credentials()
    if not verify_password(password, user.password_hash):
        raise _invalid_credentials()

    tokens = _issue_tokens(db, user.id)
    db.commit()
    return tokens


def refresh(db: Session, refresh_token: str) -> TokenPair:
    payload = _decode(refresh_token, REFRESH_TOKEN_TYPE)
    stored = get_refresh_token_by_jti(db, payload.jti)
    if stored is None or stored.user_id != payload.user_id:
        raise invalid_token_error()
    if not hmac.compare_digest(stored.token_hash, hash_token(refresh_token)):
        raise invalid_token_error()

    # 기존 토큰 삭제와 새 토큰 저장을 한 트랜잭션으로 묶는다 (ADR 0006)
    try:
        if delete_refresh_token(db, stored.jti) != 1:
            # 같은 토큰으로 들어온 다른 요청이 먼저 교체한 경우
            raise invalid_token_error()
        tokens = _issue_tokens(db, payload.user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return tokens


def logout(db: Session, refresh_token: str) -> None:
    # 이미 무효화되거나 만료된 토큰도 성공으로 처리하므로 만료는 검사하지 않는다 (멱등)
    payload = _decode(refresh_token, REFRESH_TOKEN_TYPE, verify_exp=False)
    stored = get_refresh_token_by_jti(db, payload.jti)
    if stored is None or not hmac.compare_digest(stored.token_hash, hash_token(refresh_token)):
        return
    delete_refresh_token(db, stored.jti)
    db.commit()


def get_current_user(db: Session, access_token: str) -> User:
    payload = _decode(access_token, ACCESS_TOKEN_TYPE)
    user = get_user_by_id(db, payload.user_id)
    if user is None:
        raise invalid_token_error()
    return user


def _decode(token: str, expected_type: str, *, verify_exp: bool = True) -> TokenPayload:
    try:
        return decode_token(token, expected_type, verify_exp=verify_exp)
    except TokenExpiredError as exc:
        raise _token_expired() from exc
    except InvalidTokenError as exc:
        raise invalid_token_error() from exc


def _issue_tokens(db: Session, user_id: int) -> TokenPair:
    """새 리프레시 토큰을 세션에 추가만 한다. commit은 호출하는 쪽에서 한다."""
    now = _now()
    refresh_token = create_refresh_token(user_id, now)
    add_refresh_token(
        db,
        user_id=user_id,
        jti=refresh_token.jti,
        token_hash=hash_token(refresh_token.token),
        expires_at=refresh_token.expires_at,
        created_at=now,
    )
    return TokenPair(
        access_token=create_access_token(user_id, now),
        refresh_token=refresh_token.token,
    )


def _is_valid_password(password: str) -> bool:
    try:
        password_bytes = password.encode()
    except UnicodeEncodeError:
        # 짝이 없는 서로게이트 문자처럼 UTF-8로 인코딩할 수 없는 입력 (ADR 0008)
        return False
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and len(password_bytes) <= MAX_PASSWORD_BYTES
        and ASCII_LETTER.search(password) is not None
        and DIGIT.search(password) is not None
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _email_already_exists() -> AppError:
    return AppError(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다")


def _invalid_credentials() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "INVALID_CREDENTIALS",
        "이메일 또는 비밀번호가 올바르지 않습니다",
    )


def invalid_token_error() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "유효하지 않은 토큰입니다")


def unauthorized_error() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "인증이 필요합니다")


def _token_expired() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "만료된 토큰입니다")
