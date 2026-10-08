import hashlib
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_dummy_password,
    verify_password,
)
from tests.conftest import TEST_SECRET_KEY

NOW = datetime(2026, 10, 8, 9, 30, tzinfo=UTC)


def _decode(token: str) -> dict[str, object]:
    return jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})


def test_hash_password_does_not_store_plain_text() -> None:
    password_hash = hash_password("password123")

    assert password_hash != "password123"
    assert password_hash.startswith("$2b$04$")


def test_verify_password_matches_only_original_password() -> None:
    password_hash = hash_password("password123")

    assert verify_password("password123", password_hash)
    assert not verify_password("password124", password_hash)


def test_verify_password_rejects_over_72_bytes_without_error() -> None:
    password_hash = hash_password("a1" * 36)

    assert not verify_password("a1" * 36 + "x", password_hash)


def test_verify_dummy_password_runs_without_error() -> None:
    verify_dummy_password("password123")


def test_access_token_contains_required_claims() -> None:
    payload = _decode(create_access_token(1, NOW))

    assert payload["sub"] == "1"
    assert payload["type"] == "access"
    assert payload["iat"] == int(NOW.timestamp())
    assert payload["exp"] == int((NOW + timedelta(minutes=30)).timestamp())
    assert "jti" not in payload


def test_refresh_token_contains_jti_and_expiry() -> None:
    issued = create_refresh_token(1, NOW)
    payload = _decode(issued.token)

    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"
    assert payload["jti"] == issued.jti
    assert payload["exp"] == int((NOW + timedelta(days=7)).timestamp())
    assert issued.expires_at == NOW + timedelta(days=7)


def test_refresh_tokens_issued_at_same_time_are_different() -> None:
    first = create_refresh_token(1, NOW)
    second = create_refresh_token(1, NOW)

    assert first.jti != second.jti
    assert first.token != second.token


def test_hash_token_uses_sha256() -> None:
    assert hash_token("token") == hashlib.sha256(b"token").hexdigest()


def test_token_is_signed_with_secret_key() -> None:
    token = create_access_token(1, NOW)

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "x" * 32, algorithms=["HS256"], options={"verify_exp": False})
