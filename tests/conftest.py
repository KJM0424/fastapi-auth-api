from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory

TEST_SECRET_KEY = "test-secret-key-for-pytest-0123456789"


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    # 로컬 셸 환경 변수와 프로젝트 루트의 .env가 테스트에 섞이지 않게 한다
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET_KEY)
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
