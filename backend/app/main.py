from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.aggregators.game import GameAggregator
from app.ai import OllamaProvider
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory
from app.providers.igdb import IgdbProvider
from app.providers.rawg import RawgProvider
from app.providers.steam import SteamProvider


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        rawg_key = app_settings.rawg_api_key
        rawg_provider = (
            RawgProvider(
                rawg_key,
                timeout_seconds=app_settings.rawg_timeout_seconds,
            )
            if rawg_key is not None and rawg_key.get_secret_value().strip()
            else None
        )
        steam_provider = SteamProvider(
            api_key=app_settings.steam_api_key,
            base_url=app_settings.steam_base_url,
            api_base_url=app_settings.steam_api_base_url,
            timeout_seconds=app_settings.steam_timeout_seconds,
        )
        igdb_provider = None
        if app_settings.igdb_enabled:
            client_id = app_settings.igdb_client_id
            client_secret = app_settings.igdb_client_secret
            if (
                client_id is None
                or not client_id.get_secret_value().strip()
                or client_secret is None
                or not client_secret.get_secret_value().strip()
            ):
                raise ValueError(
                    "IGDB_CLIENT_ID and IGDB_CLIENT_SECRET are required when "
                    "IGDB_ENABLED=true."
                )
            igdb_provider = IgdbProvider(
                client_id,
                client_secret,
                base_url=app_settings.igdb_base_url,
                auth_url=app_settings.igdb_auth_url,
                timeout_seconds=app_settings.igdb_timeout_seconds,
                requests_per_second=app_settings.igdb_rate_limit_per_second,
                max_concurrency=app_settings.igdb_max_concurrency,
            )
        ai_provider = None
        provider_name = app_settings.ai_provider.strip().casefold()
        if provider_name == "ollama":
            ai_provider = OllamaProvider(
                base_url=app_settings.ollama_base_url,
                model=app_settings.ollama_model,
                timeout_seconds=app_settings.ai_timeout_seconds,
                num_ctx=app_settings.ollama_num_ctx,
                max_tokens=app_settings.ollama_max_tokens,
            )
        elif provider_name not in {"none", "disabled"}:
            raise ValueError(f"Unsupported AI_PROVIDER: {app_settings.ai_provider}")
        engine = create_database_engine(app_settings.database_url)
        application.state.settings = app_settings
        application.state.rawg_provider = rawg_provider
        application.state.steam_provider = steam_provider
        application.state.igdb_provider = igdb_provider
        application.state.ai_provider = ai_provider
        application.state.db_engine = engine
        application.state.session_factory = create_session_factory(engine)
        additional_providers = [steam_provider]
        if igdb_provider is not None:
            additional_providers.insert(0, igdb_provider)
        application.state.game_aggregator = (
            GameAggregator(rawg_provider, additional_providers)
            if rawg_provider is not None
            else None
        )
        try:
            yield
        finally:
            if rawg_provider is not None:
                await rawg_provider.aclose()
            await steam_provider.aclose()
            if igdb_provider is not None:
                await igdb_provider.aclose()
            if ai_provider is not None:
                await ai_provider.aclose()
            await engine.dispose()

    application = FastAPI(title="GameScope API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(api_router)

    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
