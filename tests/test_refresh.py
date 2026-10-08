import threading
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_session_factory
from app.main import create_app
from app.models import RefreshToken
from app.services import auth_service
from tests.conftest import TEST_SECRET_KEY

REFRESH_URL = "/api/v1/auth/refresh"
INVALID_TOKEN = {"code": "INVALID_TOKEN", "message": "유효하지 않은 토큰입니다"}


@pytest.fixture
def refresh_token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/signup", json={"email": "user@example.com", "password": "password123"}
    )
    return _login(client)


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    return response.json()["refresh_token"]


def _refresh(client: TestClient, token: str) -> httpx.Response:
    return client.post(REFRESH_URL, json={"refresh_token": token})


def _stored_jtis() -> set[str]:
    with get_session_factory()() as session:
        return set(session.scalars(select(RefreshToken.jti)).all())


def _jti(token: str) -> str:
    return jwt.decode(token, TEST_SECRET_KEY, algorithms=["HS256"])["jti"]


def test_refresh_returns_new_tokens(client: TestClient, refresh_token: str) -> None:
    response = _refresh(client, refresh_token)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert body["refresh_token"] != refresh_token


def test_refresh_replaces_stored_token(client: TestClient, refresh_token: str) -> None:
    new_token = _refresh(client, refresh_token).json()["refresh_token"]

    assert _stored_jtis() == {_jti(new_token)}


def test_used_refresh_token_cannot_be_reused(client: TestClient, refresh_token: str) -> None:
    _refresh(client, refresh_token)

    response = _refresh(client, refresh_token)

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_new_refresh_token_can_be_used(client: TestClient, refresh_token: str) -> None:
    new_token = _refresh(client, refresh_token).json()["refresh_token"]

    assert _refresh(client, new_token).status_code == 200


def test_refresh_rejects_expired_token(client: TestClient, refresh_token: str) -> None:
    expired = security.create_refresh_token(1, datetime.now(UTC) - timedelta(days=8))

    response = _refresh(client, expired.token)

    assert response.status_code == 401
    assert response.json() == {"code": "TOKEN_EXPIRED", "message": "만료된 토큰입니다"}


def test_refresh_rejects_access_token(client: TestClient, refresh_token: str) -> None:
    access_token = security.create_access_token(1, datetime.now(UTC))

    assert _refresh(client, access_token).json() == INVALID_TOKEN


def test_refresh_rejects_signed_token_not_in_db(client: TestClient, refresh_token: str) -> None:
    unknown = security.create_refresh_token(1, datetime.now(UTC))

    response = _refresh(client, unknown.token)

    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_refresh_rejects_token_with_different_hash(client: TestClient, refresh_token: str) -> None:
    with get_session_factory()() as session:
        stored = session.scalars(select(RefreshToken)).one()
        stored.token_hash = "0" * 64
        session.commit()

    response = _refresh(client, refresh_token)

    assert response.json() == INVALID_TOKEN
    assert _stored_jtis() == {_jti(refresh_token)}


@pytest.mark.parametrize("token", ["not-a-jwt", ""])
def test_refresh_rejects_malformed_token(client: TestClient, token: str) -> None:
    assert _refresh(client, token).json() == INVALID_TOKEN


def test_refresh_rejects_missing_field(client: TestClient) -> None:
    response = client.post(REFRESH_URL, json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_concurrent_refresh_issues_only_once(
    refresh_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """같은 토큰으로 두 요청이 동시에 들어오면 하나만 새 토큰을 받는다 (ADR 0006)."""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        # 두 요청이 모두 DB 행을 조회한 뒤에 삭제하도록 맞춘다
        barrier = threading.Barrier(2)
        original_get = auth_service.get_refresh_token_by_jti

        def get_then_wait(db: Session, jti: str) -> RefreshToken | None:
            stored = original_get(db, jti)
            barrier.wait(timeout=5)
            return stored

        monkeypatch.setattr(auth_service, "get_refresh_token_by_jti", get_then_wait)

        responses: list[httpx.Response] = []

        def send() -> None:
            responses.append(_refresh(client, refresh_token))

        threads = [threading.Thread(target=send) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 401]
    succeeded = next(response for response in responses if response.status_code == 200)
    failed = next(response for response in responses if response.status_code == 401)
    assert failed.json() == INVALID_TOKEN
    assert _stored_jtis() == {_jti(succeeded.json()["refresh_token"])}


def test_rotation_rolls_back_delete_when_saving_new_token_fails(
    refresh_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """기존 토큰 삭제 후 새 토큰 저장이 DB 제약으로 실패하면 삭제도 함께 롤백된다 (ADR 0006)."""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        other_session_token = _login(client)
        before = _stored_jtis()

        # 삭제가 실제로 실행됐는지 기록한다
        deleted_counts: list[int] = []
        original_delete = auth_service.delete_refresh_token

        def spy_delete(db: Session, jti: str) -> int:
            count = original_delete(db, jti)
            deleted_counts.append(count)
            return count

        # 새 토큰의 jti를 다른 세션의 jti와 같게 만들어 commit 때 unique 제약 위반을 일으킨다
        original_create = auth_service.create_refresh_token

        def create_with_duplicate_jti(user_id: int, now: datetime) -> security.IssuedRefreshToken:
            issued = original_create(user_id, now)
            return security.IssuedRefreshToken(
                token=issued.token, jti=_jti(other_session_token), expires_at=issued.expires_at
            )

        monkeypatch.setattr(auth_service, "delete_refresh_token", spy_delete)
        monkeypatch.setattr(auth_service, "create_refresh_token", create_with_duplicate_jti)

        response = _refresh(client, refresh_token)

        assert response.status_code == 500
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert deleted_counts == [1]  # 기존 토큰 삭제는 실행됐다
        assert _stored_jtis() == before  # 그러나 롤백되어 기존 토큰이 남아 있고 새 토큰은 없다

        monkeypatch.setattr(auth_service, "create_refresh_token", original_create)
        assert _refresh(client, refresh_token).status_code == 200  # 기존 토큰을 계속 쓸 수 있다
