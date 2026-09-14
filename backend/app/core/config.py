from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rawg_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("RAWG_API_KEY", "GAMESCOPE_RAWG_API_KEY"),
    )
    database_url: str | None = None
    openai_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
