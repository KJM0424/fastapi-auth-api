from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    secret_key: SecretStr = Field(min_length=32)
    database_url: str = "sqlite:///./app.db"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    bcrypt_rounds: int = Field(default=12, ge=4, le=31)


@lru_cache
def get_settings() -> Settings:
    return Settings()
