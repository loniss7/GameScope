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
    steam_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("STEAM_API_KEY", "GAMESCOPE_STEAM_API_KEY"),
    )
    steam_timeout_seconds: float = Field(default=10.0, gt=0)
    steam_base_url: str = "https://store.steampowered.com/"
    steam_api_base_url: str = "https://api.steampowered.com/"
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    cache_ttl_seconds: int = Field(default=86400, gt=0)
    igdb_enabled: bool = False
    igdb_client_id: SecretStr | None = None
    igdb_client_secret: SecretStr | None = None
    igdb_base_url: str = "https://api.igdb.com/v4"
    igdb_auth_url: str = "https://id.twitch.tv/oauth2/token"
    igdb_timeout_seconds: float = Field(default=10.0, gt=0)
    igdb_rate_limit_per_second: int = Field(default=4, ge=1, le=4)
    igdb_max_concurrency: int = Field(default=8, ge=1, le=8)
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    # Keep the default request small enough for the 4k context used by most
    # local Ollama models.  Larger values can still be configured explicitly,
    # but the service also applies a total prompt budget.
    ai_timeout_seconds: float = Field(default=300.0, gt=0)
    ai_max_reviews: int = Field(default=10, ge=1, le=100)
    ai_max_review_chars: int = Field(default=1000, ge=200, le=10000)
    ai_max_prompt_chars: int = Field(default=12000, ge=2000, le=100000)
    ollama_num_ctx: int = Field(default=4096, ge=1024, le=32768)
    ollama_max_tokens: int = Field(default=512, ge=64, le=4096)


@lru_cache
def get_settings() -> Settings:
    return Settings()
