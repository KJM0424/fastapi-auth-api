import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_use_default_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./app.db"
    assert settings.access_token_expire_minutes == 30
    assert settings.refresh_token_expire_days == 7


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")

    settings = Settings(_env_file=None)

    assert settings.secret_key == "test-secret-key"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 14


def test_settings_require_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_treat_empty_secret_key_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_use_default_for_empty_optional_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "")

    settings = Settings(_env_file=None)

    assert settings.access_token_expire_minutes == 30
