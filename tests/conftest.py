from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
