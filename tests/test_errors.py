import logging

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, register_exception_handlers


class Item(BaseModel):
    name: str


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    def raise_app_error() -> None:
        raise AppError(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "이미 가입된 이메일입니다")

    @app.post("/items")
    def create_item(item: Item) -> Item:
        return item

    @app.get("/bad-request")
    def raise_unlisted_http_exception() -> None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unlisted detail")

    @app.get("/boom")
    def raise_unexpected_error() -> None:
        raise RuntimeError("secret detail")

    return TestClient(app, raise_server_exceptions=False)


def test_app_error_uses_common_format(client: TestClient) -> None:
    response = client.get("/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "EMAIL_ALREADY_EXISTS",
        "message": "이미 가입된 이메일입니다",
    }


def test_missing_field_returns_validation_error(client: TestClient) -> None:
    response = client.post("/items", json={})

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "요청 형식이 올바르지 않습니다",
    }


def test_invalid_json_returns_validation_error(client: TestClient) -> None:
    response = client.post(
        "/items", content="{invalid", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unknown_path_returns_not_found(client: TestClient) -> None:
    response = client.get("/unknown")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "요청한 경로를 찾을 수 없습니다"}


def test_wrong_method_returns_method_not_allowed(client: TestClient) -> None:
    response = client.delete("/items")

    assert response.status_code == 405
    assert response.json() == {
        "code": "METHOD_NOT_ALLOWED",
        "message": "허용되지 않은 메서드입니다",
    }
    assert response.headers["allow"] == "POST"


def test_unexpected_error_hides_detail(client: TestClient) -> None:
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_ERROR", "message": "서버 내부 오류가 발생했습니다"}
    assert "secret detail" not in response.text


def test_unlisted_http_exception_returns_internal_error(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.core.errors"):
        response = client.get("/bad-request")

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_ERROR", "message": "서버 내부 오류가 발생했습니다"}
    assert "unlisted detail" not in response.text
    assert "400" in caplog.text
