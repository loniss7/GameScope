from abc import ABC, abstractmethod

from app.schemas import Game


class GameProviderError(RuntimeError):
    """Base class for sanitized errors raised by external providers."""


class GameProvider(ABC):
    """Contract for a source that searches and fetches normalized games."""

    @property
    def name(self) -> str:
        return type(self).__name__.removesuffix("Provider").casefold()

    @abstractmethod
    async def search(self, query: str) -> list[Game]:
        """Return normalized games matching a text query."""
        raise NotImplementedError

    @abstractmethod
    async def get_game(self, external_id: str) -> Game | None:
        """Return a normalized game, or None when the provider has no such game."""
        raise NotImplementedError
