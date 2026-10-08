from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core import security
from app.db.session import get_session_factory
from app.models import RefreshToken, User

ME_URL = "/api/v1/users/me"
INVALID_TOKEN = {"code": "INVALID_TOKEN", "message": "유효하지 않은 토큰입니다"}


@pytest.fixture
def tokens(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/signup", json={"email": "user@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    return response.json()


def _me(client: TestClient, authorization: str | None) -> httpx.Response:
    headers = {} if authorization is None else {"Authorization": authorization}
    return client.get(ME_URL, headers=headers)


def test_me_returns_current_user(client: TestClient, tokens: dict[str, str]) -> None:
    response = _me(client, f"Bearer {tokens['access_token']}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "created_at"}
    assert body["email"] == "user@example.com"


def test_me_accepts_lowercase_bearer_scheme(client: TestClient, tokens: dict[str, str]) -> None:
    assert _me(client, f"bearer {tokens['access_token']}").status_code == 200


@pytest.mark.parametrize("authorization", [None, "", "   "])
def test_me_requires_authorization_header(client: TestClient, authorization: str | None) -> None:
    response = _me(client, authorization)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED", "message": "인증이 필요합니다"}


@pytest.mark.parametrize(
    "authorization",
    ["Basic dXNlcjpwYXNz", "Bearer", "Bearer ", "token-without-scheme", "Bearer not-a-jwt"],
)
def test_me_rejects_invalid_authorization(client: TestClient, authorization: str) -> None:
    response = _me(client, authorization)

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_me_rejects_refresh_token(client: TestClient, tokens: dict[str, str]) -> None:
    assert _me(client, f"Bearer {tokens['refresh_token']}").json() == INVALID_TOKEN


def test_me_rejects_expired_access_token(client: TestClient, tokens: dict[str, str]) -> None:
    expired = security.create_access_token(1, datetime.now(UTC) - timedelta(minutes=31))

    response = _me(client, f"Bearer {expired}")

    assert response.status_code == 401
    assert response.json() == {"code": "TOKEN_EXPIRED", "message": "만료된 토큰입니다"}


def test_me_rejects_token_of_missing_user(client: TestClient, tokens: dict[str, str]) -> None:
    with get_session_factory()() as session:
        session.execute(delete(RefreshToken))
        session.execute(delete(User))
        session.commit()

    response = _me(client, f"Bearer {tokens['access_token']}")

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_me_does_not_return_password_hash(client: TestClient, tokens: dict[str, str]) -> None:
    response = _me(client, f"Bearer {tokens['access_token']}")

    assert "password" not in response.text
    assert "$2b$" not in response.text
