import logging

from app.matching import best_game_match
from app.providers.base import GameProvider, GameProviderError
from app.schemas import Game

logger = logging.getLogger(__name__)


def _merge_names(primary: list[str], secondary: list[str]) -> list[str]:
    result = list(primary)
    existing = {name.casefold() for name in result}
    for name in secondary:
        if name.casefold() not in existing:
            result.append(name)
            existing.add(name.casefold())
    return result


def merge_games(primary: Game, secondary: Game) -> Game:
    """Merge normalized data while preferring the primary provider's values."""
    ratings = list(primary.ratings)
    rating_sources = {rating.source.casefold() for rating in ratings}
    ratings.extend(
        rating
        for rating in secondary.ratings
        if rating.source.casefold() not in rating_sources
    )
    external_ids = dict(secondary.external_ids)
    external_ids.update(primary.external_ids)
    return Game(
        id=primary.id or secondary.id,
        title=primary.title,
        description=primary.description or secondary.description,
        release_date=primary.release_date or secondary.release_date,
        developers=_merge_names(primary.developers, secondary.developers),
        publishers=_merge_names(primary.publishers, secondary.publishers),
        genres=_merge_names(primary.genres, secondary.genres),
        categories=_merge_names(primary.categories, secondary.categories),
        platforms=_merge_names(primary.platforms, secondary.platforms),
        ratings=ratings,
        price=primary.price or secondary.price,
        system_requirements=primary.system_requirements
        or secondary.system_requirements,
        image_url=primary.image_url or secondary.image_url,
        external_ids=external_ids,
    )


class GameAggregator:
    """Combine the primary RAWG record with confidently matched providers."""

    def __init__(
        self,
        primary_provider: GameProvider,
        additional_providers: list[GameProvider] | None = None,
    ) -> None:
        self._primary = primary_provider
        self._additional = additional_providers or []

    async def search(self, query: str) -> list[Game]:
        # Keep search light: enrich a selected game on its detail request instead of
        # issuing requests to every provider for every search result.
        return await self._primary.search(query)

    async def get_game(self, external_id: str) -> Game | None:
        primary_game = await self._primary.get_game(external_id)
        if primary_game is None:
            return None
        merged_game = primary_game
        for provider in self._additional:
            try:
                candidates = await provider.search(primary_game.title)
                match = best_game_match(primary_game, candidates)
                if match is None:
                    continue
                provider_id = match.game.external_ids.get(getattr(provider, "name", ""))
                if not provider_id:
                    continue
                details = await provider.get_game(provider_id)
                if details is not None:
                    merged_game = merge_games(merged_game, details)
            except GameProviderError as error:
                logger.warning(
                    "Provider %s could not enrich game %s: %s",
                    getattr(provider, "name", type(provider).__name__),
                    external_id,
                    error,
                )
        return merged_game
