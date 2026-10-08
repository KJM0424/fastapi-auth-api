import re
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import MAX_PASSWORD_BYTES, hash_password
from app.models import User
from app.repositories.user_repository import add_user, get_user_by_email

MIN_PASSWORD_LENGTH = 8
ASCII_LETTER = re.compile(r"[A-Za-z]")
DIGIT = re.compile(r"[0-9]")


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


def _is_valid_password(password: str) -> bool:
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and len(password.encode()) <= MAX_PASSWORD_BYTES
        and ASCII_LETTER.search(password) is not None
        and DIGIT.search(password) is not None
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _email_already_exists() -> AppError:
    return AppError(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다")
