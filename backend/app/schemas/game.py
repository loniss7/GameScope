from datetime import date

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
    platforms: list[str] = Field(default_factory=list)
    ratings: list[GameRating] = Field(default_factory=list)
    image_url: str | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
