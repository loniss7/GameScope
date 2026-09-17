from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GameRating(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str = Field(min_length=1)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    rating_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def score_must_not_exceed_maximum(self) -> "GameRating":
        if self.score > self.max_score:
            raise ValueError("score must not exceed max_score")
        return self


class GamePrice(BaseModel):
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=1, max_length=8)
    discount_percent: int = Field(default=0, ge=0, le=100)


class GameSystemRequirements(BaseModel):
    minimum: str | None = None
    recommended: str | None = None


class GameReview(BaseModel):
    source: str = Field(min_length=1)
    author: str | None = None
    language: str | None = None
    text: str
    voted_up: bool
    created_at: date | None = None
    playtime_minutes: int | None = Field(default=None, ge=0)


class GameReviewsResponse(BaseModel):
    items: list[GameReview] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    source: str


class GameAchievement(BaseModel):
    name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str | None = None
    icon_url: str | None = None
    icon_gray_url: str | None = None
    hidden: bool = False


class GameAchievementsResponse(BaseModel):
    items: list[GameAchievement] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    source: str


class Game(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Internal GameScope identifier; provider IDs are stored separately below.
    id: str | None = None
    title: str = Field(min_length=1)
    description: str | None = None
    release_date: date | None = None
    developers: list[str] = Field(default_factory=list)
    publishers: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    ratings: list[GameRating] = Field(default_factory=list)
    price: GamePrice | None = None
    is_free: bool | None = None
    achievement_count: int | None = Field(default=None, ge=0)
    system_requirements: GameSystemRequirements | None = None
    image_url: str | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
