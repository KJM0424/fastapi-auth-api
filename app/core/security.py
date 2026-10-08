import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings

# bcrypt 5.0부터 72바이트를 넘는 입력은 ValueError가 난다 (ADR 0002)
MAX_PASSWORD_BYTES = 72
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


@dataclass(frozen=True)
class IssuedRefreshToken:
    token: str
    jti: str
    expires_at: datetime


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode()
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, password_hash.encode())


def verify_dummy_password(password: str) -> None:
    """가입되지 않은 이메일로 로그인할 때도 checkpw를 실행해 응답 시간을 맞춘다 (ADR 0008)."""
    verify_password(password, _dummy_password_hash(get_settings().bcrypt_rounds))


@lru_cache
def _dummy_password_hash(rounds: int) -> str:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(secrets.token_bytes(32), salt).decode()


def create_access_token(user_id: int, now: datetime) -> str:
    expires_at = now + timedelta(minutes=get_settings().access_token_expire_minutes)
    payload = {"sub": str(user_id), "type": ACCESS_TOKEN_TYPE, "iat": now, "exp": expires_at}
    return _encode(payload)


def create_refresh_token(user_id: int, now: datetime) -> IssuedRefreshToken:
    jti = secrets.token_hex(16)
    expires_at = now + timedelta(days=get_settings().refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": REFRESH_TOKEN_TYPE,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    return IssuedRefreshToken(token=_encode(payload), jti=jti, expires_at=expires_at)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _encode(payload: dict[str, object]) -> str:
    secret_key = get_settings().secret_key.get_secret_value()
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)
