from pathlib import Path

from fastapi.testclient import TestClient

from app.core import security
from app.main import create_app


def test_app_starts_and_creates_database(tmp_path: Path) -> None:
    with TestClient(create_app()) as client:
        response = client.get("/unknown")

    assert (tmp_path / "test.db").exists()
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_app_startup_prepares_dummy_password_hash() -> None:
    security._dummy_password_hash.cache_clear()

    with TestClient(create_app()):
        assert security._dummy_password_hash.cache_info().currsize == 1
