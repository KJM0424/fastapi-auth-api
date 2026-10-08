from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    _clear_caches()
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    _clear_caches()


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
