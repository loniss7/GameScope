from pathlib import Path

from pydantic import SecretStr

from app.core.config import Settings

ENV_FIXTURE = Path(__file__).with_name("settings.env")


def test_settings_load_values_from_env_file(monkeypatch) -> None:
    for name in ("RAWG_API_KEY", "DATABASE_URL", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=ENV_FIXTURE)

    assert settings.rawg_api_key == SecretStr("rawg-from-file")
    assert settings.database_url == "sqlite:///from-file.db"
    assert settings.openai_api_key == SecretStr("openai-from-file")


def test_environment_variables_override_env_file(monkeypatch) -> None:
    monkeypatch.setenv("RAWG_API_KEY", "rawg-from-environment")
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-environment")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-from-environment")

    settings = Settings(_env_file=ENV_FIXTURE)

    assert settings.rawg_api_key == SecretStr("rawg-from-environment")
    assert settings.database_url == "postgresql://from-environment"
    assert settings.openai_api_key == SecretStr("openai-from-environment")


def test_legacy_gamescope_rawg_key_name_is_supported(monkeypatch) -> None:
    monkeypatch.delenv("RAWG_API_KEY", raising=False)
    monkeypatch.setenv("GAMESCOPE_RAWG_API_KEY", "legacy-rawg-key")

    settings = Settings(_env_file=None)

    assert settings.rawg_api_key == SecretStr("legacy-rawg-key")


def test_settings_are_optional_when_values_are_not_provided(monkeypatch) -> None:
    for name in (
        "RAWG_API_KEY",
        "GAMESCOPE_RAWG_API_KEY",
        "DATABASE_URL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.rawg_api_key is None
    assert settings.database_url == "sqlite+aiosqlite:///./gamescope.db"
    assert settings.openai_api_key is None


def test_legacy_database_url_name_is_supported(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "GAMESCOPE_DATABASE_URL", "postgresql+asyncpg://localhost/gamescope"
    )

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+asyncpg://localhost/gamescope"


def test_steam_api_key_aliases_are_supported(monkeypatch) -> None:
    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    monkeypatch.setenv("GAMESCOPE_STEAM_API_KEY", "steam-key")

    settings = Settings(_env_file=None)

    assert settings.steam_api_key == SecretStr("steam-key")


def test_ai_settings_have_ollama_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.ai_provider == "ollama"
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "qwen3:8b"
    assert settings.ai_timeout_seconds == 300
    assert settings.ai_max_reviews == 10
    assert settings.ai_max_review_chars == 1000
    assert settings.ai_max_prompt_chars == 12000
    assert settings.ollama_num_ctx == 4096
    assert settings.ollama_max_tokens == 512


def test_igdb_settings_have_safe_disabled_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.igdb_enabled is False
    assert settings.igdb_client_id is None
    assert settings.igdb_client_secret is None
    assert settings.igdb_base_url == "https://api.igdb.com/v4"
    assert settings.igdb_auth_url == "https://id.twitch.tv/oauth2/token"
    assert settings.igdb_rate_limit_per_second == 4
    assert settings.igdb_max_concurrency == 8
