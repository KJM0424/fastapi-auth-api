import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from tests.conftest import TEST_SECRET_KEY


def test_settings_use_default_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./app.db"
    assert settings.access_token_expire_minutes == 30
    assert settings.refresh_token_expire_days == 7


def test_settings_use_default_bcrypt_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BCRYPT_ROUNDS")

    assert Settings(_env_file=None).bcrypt_rounds == 12


@pytest.mark.parametrize("value", ["3", "32"])
def test_settings_reject_out_of_range_bcrypt_rounds(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("BCRYPT_ROUNDS", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")

    settings = Settings(_env_file=None)

    assert settings.secret_key.get_secret_value() == TEST_SECRET_KEY
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


def test_settings_reject_short_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "a" * 31)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_hide_secret_key_in_repr() -> None:
    settings = Settings(_env_file=None)

    assert TEST_SECRET_KEY not in repr(settings)


@pytest.mark.parametrize("name", ["ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_settings_reject_non_positive_expiry(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_ignores_project_env_file() -> None:
    assert get_settings().access_token_expire_minutes == 30
