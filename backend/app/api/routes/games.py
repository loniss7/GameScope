from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.ai.base import AiProviderError, AiProviderNotConfiguredError
from app.api.dependencies import get_game_service
from app.providers.base import GameProviderError
from app.providers.steam import SteamApiNotConfiguredError
from app.schemas import (
    Game,
    GameAchievementsResponse,
    GameReviewsResponse,
    GameSummary,
)
from app.services import GameService, SummaryUnavailableError

router = APIRouter(prefix="/api/games", tags=["games"])


class GameSearchResponse(BaseModel):
    items: list[Game] = Field(default_factory=list)


@router.get("/search", response_model=GameSearchResponse)
async def search_games(
    query: Annotated[
        str, Query(alias="q", min_length=1, max_length=200, pattern=r".*\S.*")
    ],
    service: Annotated[GameService, Depends(get_game_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GameSearchResponse:
    try:
        results = await service.search_games(query.strip(), limit=limit)
    except GameProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "provider_error", "message": str(error)},
        ) from error
    return GameSearchResponse(items=results)


@router.get("/{game_id}", response_model=Game)
async def get_game(
    game_id: int,
    service: Annotated[GameService, Depends(get_game_service)],
) -> Game:
    try:
        game = await service.get_game(game_id)
    except GameProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "provider_error", "message": str(error)},
        ) from error
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found."
        )
    return game


@router.get("/{game_id}/reviews", response_model=GameReviewsResponse)
async def get_game_reviews(
    game_id: int,
    service: Annotated[GameService, Depends(get_game_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GameReviewsResponse:
    try:
        reviews = await service.get_reviews(game_id, limit=limit)
    except GameProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "provider_error", "message": str(error)},
        ) from error
    if reviews is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found."
        )
    items, total = reviews
    return GameReviewsResponse(items=items, total=total, source="steam")


@router.get("/{game_id}/achievements", response_model=GameAchievementsResponse)
async def get_game_achievements(
    game_id: int,
    service: Annotated[GameService, Depends(get_game_service)],
) -> GameAchievementsResponse:
    try:
        achievements = await service.get_achievements(game_id)
    except SteamApiNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "steam_api_key_missing", "message": str(error)},
        ) from error
    except GameProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "provider_error", "message": str(error)},
        ) from error
    if achievements is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found."
        )
    return GameAchievementsResponse(
        items=achievements, total=len(achievements), source="steam"
    )


@router.get("/{game_id}/summary", response_model=GameSummary)
async def get_game_summary(
    game_id: int,
    service: Annotated[GameService, Depends(get_game_service)],
) -> GameSummary:
    summary = await service.get_summary(game_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "summary_not_found", "message": "Summary not found."},
        )
    return summary


@router.post("/{game_id}/summary", response_model=GameSummary)
async def create_game_summary(
    game_id: int,
    service: Annotated[GameService, Depends(get_game_service)],
    language: Annotated[str, Query(min_length=2, max_length=16)] = "ru",
    force_refresh: Annotated[bool, Query()] = False,
) -> GameSummary:
    try:
        summary = await service.create_summary(
            game_id,
            language=language,
            force_refresh=force_refresh,
        )
    except AiProviderNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ai_provider_unavailable", "message": str(error)},
        ) from error
    except SummaryUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "summary_unavailable", "message": str(error)},
        ) from error
    except AiProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_provider_error", "message": str(error)},
        ) from error
    except GameProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "provider_error", "message": str(error)},
        ) from error
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found."
        )
    return summary
