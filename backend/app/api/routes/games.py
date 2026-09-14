from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_game_service
from app.providers.base import GameProviderError
from app.schemas import Game, GameReviewsResponse
from app.services import GameService

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
