"""Pydantic schemas shared by the GameScope backend."""

from app.schemas.game import (
    Game,
    GamePrice,
    GameRating,
    GameReview,
    GameReviewsResponse,
    GameSystemRequirements,
)

__all__ = [
    "Game",
    "GamePrice",
    "GameRating",
    "GameReview",
    "GameReviewsResponse",
    "GameSystemRequirements",
]
