from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SummarySentiment(BaseModel):
    positive: float = Field(default=0.0, ge=0, le=1)
    negative: float = Field(default=0.0, ge=0, le=1)
    neutral: float = Field(default=0.0, ge=0, le=1)

    @model_validator(mode="after")
    def normalize_distribution(self) -> "SummarySentiment":
        total = self.positive + self.negative + self.neutral
        if total <= 0:
            self.neutral = 1.0
            return self
        if abs(total - 1.0) > 0.001:
            self.positive /= total
            self.negative /= total
            self.neutral /= total
        return self


class GameSummary(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    pros: list[str] = Field(default_factory=list, max_length=10)
    cons: list[str] = Field(default_factory=list, max_length=10)
    sentiment: SummarySentiment = Field(default_factory=SummarySentiment)
    reviews_analyzed: int = Field(default=0, ge=0)
    reviews_total: int = Field(default=0, ge=0)
    model: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=40)
    language: str = Field(default="ru", min_length=2, max_length=16)
    generated_at: datetime | None = None
