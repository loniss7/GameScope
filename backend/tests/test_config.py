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


def test_settings_are_optional_when_values_are_not_provided(monkeypatch) -> None:
    for name in ("RAWG_API_KEY", "DATABASE_URL", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.rawg_api_key is None
    assert settings.database_url is None
    assert settings.openai_api_key is None
