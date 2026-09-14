from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.aggregators.game import GameAggregator
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory
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
            base_url=app_settings.steam_base_url,
            timeout_seconds=app_settings.steam_timeout_seconds,
        )
        engine = create_database_engine(app_settings.database_url)
        application.state.settings = app_settings
        application.state.rawg_provider = rawg_provider
        application.state.steam_provider = steam_provider
        application.state.db_engine = engine
        application.state.session_factory = create_session_factory(engine)
        application.state.game_aggregator = (
            GameAggregator(rawg_provider, [steam_provider])
            if rawg_provider is not None
            else None
        )
        try:
            yield
        finally:
            if rawg_provider is not None:
                await rawg_provider.aclose()
            await steam_provider.aclose()
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
