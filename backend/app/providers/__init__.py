"""External game data provider contracts and implementations."""

from app.providers.base import GameProvider, GameProviderError
from app.providers.igdb import (
    IgdbAuthenticationError,
    IgdbProvider,
    IgdbProviderError,
    IgdbTokenManager,
    map_igdb_game,
)

__all__ = [
    "GameProvider",
    "GameProviderError",
    "IgdbAuthenticationError",
    "IgdbProvider",
    "IgdbProviderError",
    "IgdbTokenManager",
    "map_igdb_game",
]
