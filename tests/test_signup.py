import re

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import User
from app.services import auth_service

SIGNUP_URL = "/api/v1/auth/signup"
PASSWORD_POLICY_MESSAGE = "비밀번호는 8자 이상, 72바이트 이하이며 영문과 숫자를 포함해야 합니다"


def _signup(
    client: TestClient, email: str = "user@example.com", password: str = "password123"
) -> httpx.Response:
    return client.post(SIGNUP_URL, json={"email": email, "password": password})


def test_signup_returns_created_user(client: TestClient) -> None:
    response = _signup(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "created_at"}
    assert body["email"] == "user@example.com"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", body["created_at"])


def test_signup_stores_lowercase_email_and_hashed_password(client: TestClient) -> None:
    response = _signup(client, email="User@Example.com")

    assert response.json()["email"] == "user@example.com"
    with get_session_factory()() as session:
        user = session.scalars(select(User)).one()
    assert user.email == "user@example.com"
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2b$")


def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    _signup(client)

    response = _signup(client, email="USER@example.com")

    assert response.status_code == 409
    assert response.json() == {
        "code": "EMAIL_ALREADY_EXISTS",
        "message": "이미 가입된 이메일입니다",
    }


def test_signup_returns_conflict_when_unique_constraint_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signup(client)
    # 중복 확인을 통과한 두 요청이 동시에 저장하는 경우를 흉내 낸다
    monkeypatch.setattr(auth_service, "get_user_by_email", lambda db, email: None)

    response = _signup(client)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "password123"},
        {"email": "user@example.com"},
        {"password": "password123"},
        {"email": "user@example.com", "password": 12345678},
    ],
)
def test_signup_rejects_invalid_request(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post(SIGNUP_URL, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "password",
    [
        "abcdef1",  # 7자
        "abcdefgh",  # 숫자 없음
        "12345678",  # 영문 없음
        "가나다라마바사1",  # ASCII 영문 없음
        "a1" * 36 + "b",  # 73바이트
        "a1" + "가" * 24,  # 26자지만 74바이트
    ],
)
def test_signup_rejects_password_policy_violation(client: TestClient, password: str) -> None:
    response = _signup(client, password=password)

    assert response.status_code == 422
    assert response.json() == {"code": "INVALID_PASSWORD", "message": PASSWORD_POLICY_MESSAGE}


def test_signup_rejects_unencodable_password(client: TestClient) -> None:
    response = client.post(
        SIGNUP_URL,
        content='{"email": "user@example.com", "password": "abc12345\\ud800"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "INVALID_PASSWORD", "message": PASSWORD_POLICY_MESSAGE}


@pytest.mark.parametrize("password", ["abcdefg1", "a1" * 36, "a1가나다라마바"])
def test_signup_accepts_password_on_boundary(client: TestClient, password: str) -> None:
    assert _signup(client, password=password).status_code == 201


def test_signup_does_not_store_user_when_rejected(client: TestClient) -> None:
    _signup(client, password="short1")

    with get_session_factory()() as session:
        assert _count_users(session) == 0


def _count_users(session: Session) -> int:
    return len(session.scalars(select(User)).all())
