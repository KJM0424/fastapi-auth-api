import hashlib
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
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


def test_hash_password_rejects_over_72_bytes() -> None:
    with pytest.raises(ValueError):
        hash_password("a1" * 36 + "x")


def test_verify_password_matches_only_original_password() -> None:
    password_hash = hash_password("password123")

    assert verify_password("password123", password_hash)
    assert not verify_password("password124", password_hash)


def test_verify_password_rejects_over_72_bytes_without_error() -> None:
    password_hash = hash_password("a1" * 36)

    assert not verify_password("a1" * 36 + "x", password_hash)


def test_verify_password_rejects_unencodable_input_without_error() -> None:
    password_hash = hash_password("password123")

    assert not verify_password("password123\ud800", password_hash)


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


def _encode(payload: dict[str, object], key: str = TEST_SECRET_KEY) -> str:
    return jwt.encode(payload, key, algorithm="HS256")


def _valid_payload(**overrides: object) -> dict[str, object]:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": "1",
        "type": "refresh",
        "jti": "a" * 32,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def test_decode_token_returns_payload() -> None:
    issued = create_refresh_token(1, datetime.now(UTC))

    payload = decode_token(issued.token, "refresh")

    assert payload.user_id == 1
    assert payload.jti == issued.jti


def test_decode_access_token_has_no_jti() -> None:
    token = create_access_token(1, datetime.now(UTC))

    assert decode_token(token, "access").jti is None


def test_decode_token_rejects_expired_token() -> None:
    token = create_access_token(1, datetime.now(UTC) - timedelta(minutes=31))

    with pytest.raises(TokenExpiredError):
        decode_token(token, "access")


def test_decode_token_can_skip_expiry_check() -> None:
    issued = create_refresh_token(1, datetime.now(UTC) - timedelta(days=8))

    assert decode_token(issued.token, "refresh", verify_exp=False).user_id == 1


def test_expired_token_with_wrong_signature_is_invalid_not_expired() -> None:
    token = _encode(_valid_payload(exp=datetime.now(UTC) - timedelta(minutes=1)), key="x" * 32)

    with pytest.raises(InvalidTokenError):
        decode_token(token, "refresh")


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        "",
        _encode(_valid_payload(), key="x" * 32),  # 다른 키로 서명
        _encode(_valid_payload(type="access")),  # 종류 불일치
        _encode(_valid_payload(jti=None)),  # jti 없음
        _encode(_valid_payload(sub=None)),  # sub 없음
        _encode(_valid_payload(sub="abc")),  # sub가 숫자가 아님
        _encode(_valid_payload(exp=None)),  # exp 없음
    ],
)
def test_decode_token_rejects_invalid_token(token: str) -> None:
    with pytest.raises(InvalidTokenError):
        decode_token(token, "refresh")


def test_decode_token_rejects_none_algorithm() -> None:
    token = jwt.encode(_valid_payload(), None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_token(token, "refresh")
