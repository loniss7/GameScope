"""Pydantic schemas shared by the GameScope backend."""

from app.schemas.ai import GameSummary, SummarySentiment
from app.schemas.game import (
    Game,
    GameAchievement,
    GameAchievementsResponse,
    GamePrice,
    GameRating,
    GameReview,
    GameReviewsResponse,
    GameSystemRequirements,
)

__all__ = [
    "Game",
    "GameAchievement",
    "GameAchievementsResponse",
    "GamePrice",
    "GameRating",
    "GameReview",
    "GameReviewsResponse",
    "GameSummary",
    "GameSystemRequirements",
    "SummarySentiment",
]
