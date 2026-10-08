from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_starts_and_creates_database(tmp_path: Path) -> None:
    with TestClient(create_app()) as client:
        response = client.get("/unknown")

    assert (tmp_path / "test.db").exists()
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
