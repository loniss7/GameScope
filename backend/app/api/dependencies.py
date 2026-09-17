from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AiProvider
from app.services import GameService


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "database_unavailable",
                "message": "Database is not configured.",
            },
        )
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_game_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GameService:
    aggregator = getattr(request.app.state, "game_aggregator", None)
    steam_provider = getattr(request.app.state, "steam_provider", None)
    ai_provider: AiProvider | None = getattr(request.app.state, "ai_provider", None)
    settings = getattr(request.app.state, "settings", None)
    if aggregator is None or steam_provider is None or settings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "providers_unavailable",
                "message": "Game providers are not configured.",
            },
        )
    return GameService(
        session,
        aggregator,
        steam_provider,
        ai_provider=ai_provider,
        ai_max_reviews=settings.ai_max_reviews,
        ai_max_review_chars=settings.ai_max_review_chars,
        ai_max_prompt_chars=settings.ai_max_prompt_chars,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
