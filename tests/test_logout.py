from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import security
from app.db.session import get_session_factory
from app.models import RefreshToken

LOGOUT_URL = "/api/v1/auth/logout"
INVALID_TOKEN = {"code": "INVALID_TOKEN", "message": "유효하지 않은 토큰입니다"}


@pytest.fixture
def refresh_token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/signup", json={"email": "user@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    return response.json()["refresh_token"]


def _logout(client: TestClient, token: str) -> httpx.Response:
    return client.post(LOGOUT_URL, json={"refresh_token": token})


def _count_tokens() -> int:
    with get_session_factory()() as session:
        return len(session.scalars(select(RefreshToken)).all())


def _store_expired_token(user_id: int) -> str:
    issued = security.create_refresh_token(user_id, datetime.now(UTC) - timedelta(days=8))
    with get_session_factory()() as session:
        session.add(
            RefreshToken(
                user_id=user_id,
                jti=issued.jti,
                token_hash=security.hash_token(issued.token),
                expires_at=issued.expires_at,
                created_at=datetime.now(UTC) - timedelta(days=8),
            )
        )
        session.commit()
    return issued.token


def test_logout_deletes_refresh_token(client: TestClient, refresh_token: str) -> None:
    response = _logout(client, refresh_token)

    assert response.status_code == 204
    assert response.content == b""
    assert _count_tokens() == 0


def test_logged_out_token_cannot_refresh(client: TestClient, refresh_token: str) -> None:
    _logout(client, refresh_token)

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.json() == INVALID_TOKEN


def test_logout_is_idempotent(client: TestClient, refresh_token: str) -> None:
    _logout(client, refresh_token)

    assert _logout(client, refresh_token).status_code == 204


def test_logout_with_expired_token_deletes_row(client: TestClient, refresh_token: str) -> None:
    expired_token = _store_expired_token(user_id=1)
    assert _count_tokens() == 2

    response = _logout(client, expired_token)

    assert response.status_code == 204
    assert _count_tokens() == 1


def test_logout_with_different_hash_keeps_row(client: TestClient, refresh_token: str) -> None:
    with get_session_factory()() as session:
        stored = session.scalars(select(RefreshToken)).one()
        stored.token_hash = "0" * 64
        session.commit()

    response = _logout(client, refresh_token)

    assert response.status_code == 204
    assert _count_tokens() == 1


@pytest.mark.parametrize("token", ["not-a-jwt", ""])
def test_logout_rejects_malformed_token(client: TestClient, token: str) -> None:
    response = _logout(client, token)

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_logout_rejects_access_token(client: TestClient, refresh_token: str) -> None:
    access_token = security.create_access_token(1, datetime.now(UTC))

    response = _logout(client, access_token)

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN
    assert _count_tokens() == 1


def test_logout_only_deletes_given_session(client: TestClient, refresh_token: str) -> None:
    client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})

    _logout(client, refresh_token)

    assert _count_tokens() == 1


def test_logout_rejects_missing_field(client: TestClient) -> None:
    response = client.post(LOGOUT_URL, json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(("length", "status_code"), [(2048, 401), (2049, 422)])
def test_refresh_token_length_limit(client: TestClient, length: int, status_code: int) -> None:
    response = client.post(LOGOUT_URL, json={"refresh_token": "a" * length})

    assert response.status_code == status_code
