from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    rawg_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("RAWG_API_KEY", "GAMESCOPE_RAWG_API_KEY"),
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./gamescope.db",
        validation_alias=AliasChoices("DATABASE_URL", "GAMESCOPE_DATABASE_URL"),
    )
    openai_api_key: SecretStr | None = None
    rawg_timeout_seconds: float = Field(default=10.0, gt=0)
    steam_timeout_seconds: float = Field(default=10.0, gt=0)
    steam_base_url: str = "https://store.steampowered.com/"
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    cache_ttl_seconds: int = Field(default=86400, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
