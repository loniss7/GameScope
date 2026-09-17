from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas import GameReview, GameSummary


class AiProviderError(RuntimeError):
    """Base class for sanitized AI provider errors."""


class AiProviderNotConfiguredError(AiProviderError):
    """Raised when no AI provider is enabled for a requested operation."""


class AiProvider(ABC):
    """Contract for a provider that summarizes normalized game reviews."""

    @property
    def name(self) -> str:
        return type(self).__name__.removesuffix("Provider").casefold()

    @abstractmethod
    async def summarize_reviews(
        self,
        game_title: str,
        reviews: Sequence[GameReview],
        *,
        language: str = "ru",
    ) -> GameSummary:
        """Return a structured summary for the supplied reviews."""
        raise NotImplementedError

    async def aclose(self) -> None:
        """Release provider resources."""
