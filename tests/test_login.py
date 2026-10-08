import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import security
from app.db.session import get_session_factory
from app.models import RefreshToken
from tests.conftest import TEST_SECRET_KEY

LOGIN_URL = "/api/v1/auth/login"
INVALID_CREDENTIALS = {
    "code": "INVALID_CREDENTIALS",
    "message": "이메일 또는 비밀번호가 올바르지 않습니다",
}


@pytest.fixture(autouse=True)
def registered_user(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/signup", json={"email": "user@example.com", "password": "password123"}
    )


def _login(
    client: TestClient, email: str = "user@example.com", password: str = "password123"
) -> httpx.Response:
    return client.post(LOGIN_URL, json={"email": email, "password": password})


def _decode(token: str) -> dict[str, object]:
    return jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])


def test_login_returns_tokens(client: TestClient) -> None:
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert _decode(body["access_token"])["type"] == "access"
    assert _decode(body["refresh_token"])["type"] == "refresh"


def test_login_stores_refresh_token_hash_with_jti(client: TestClient) -> None:
    refresh_token = _login(client).json()["refresh_token"]

    with get_session_factory()() as session:
        stored = session.scalars(select(RefreshToken)).one()
    assert stored.jti == _decode(refresh_token)["jti"]
    assert stored.token_hash == security.hash_token(refresh_token)
    assert stored.token_hash != refresh_token


def test_login_ignores_email_case(client: TestClient) -> None:
    assert _login(client, email="USER@Example.com").status_code == 200


def test_each_login_adds_refresh_token(client: TestClient) -> None:
    _login(client)
    _login(client)

    with get_session_factory()() as session:
        assert len(session.scalars(select(RefreshToken)).all()) == 2


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("user@example.com", "wrongpass1"),  # 비밀번호 불일치
        ("other@example.com", "password123"),  # 가입되지 않은 이메일
        ("not-an-email", "password123"),  # 이메일 형식 오류
        ("user@example.com", "a1" * 36 + "b"),  # 72바이트 초과
    ],
)
def test_login_failure_uses_single_error(client: TestClient, email: str, password: str) -> None:
    response = _login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS


def test_login_with_unknown_email_runs_dummy_check(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.auth_service.verify_dummy_password", lambda password: calls.append(password)
    )

    _login(client, email="other@example.com")

    assert calls == ["password123"]


def test_login_failure_does_not_issue_refresh_token(client: TestClient) -> None:
    _login(client, password="wrongpass1")

    with get_session_factory()() as session:
        assert session.scalars(select(RefreshToken)).all() == []


@pytest.mark.parametrize("payload", [{"email": "user@example.com"}, {"password": "password123"}])
def test_login_rejects_missing_field(client: TestClient, payload: dict[str, str]) -> None:
    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
