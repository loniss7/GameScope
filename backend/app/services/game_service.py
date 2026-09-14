import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.game import GameAggregator
from app.providers.base import GameProviderError
from app.providers.steam import SteamProvider
from app.repositories.games import GameRepository
from app.schemas import Game, GameReview

logger = logging.getLogger(__name__)


class GameService:
    """Use cases that coordinate providers, normalized data, and persistence."""

    def __init__(
        self,
        session: AsyncSession,
        aggregator: GameAggregator,
        steam_provider: SteamProvider,
        *,
        cache_ttl_seconds: int,
    ) -> None:
        self._games = GameRepository(session)
        self._aggregator = aggregator
        self._steam = steam_provider
        self._cache_ttl_seconds = cache_ttl_seconds

    async def search_games(self, query: str, *, limit: int = 20) -> list[Game]:
        results = await self._aggregator.search(query)
        saved: list[Game] = []
        for game in results[: max(1, min(limit, 100))]:
            saved.append(await self._games.save(game, preserve_existing=True))
        return saved

    async def get_game(self, game_id: int) -> Game | None:
        record = await self._games.get_record_by_id(game_id)
        if record is None:
            return None
        cached = await self._games.get_by_id(game_id)
        if cached is None or not self._needs_refresh(record.last_synced_at):
            return cached

        rawg_id = next(
            (
                external.external_id
                for external in record.external_ids
                if external.provider == "rawg"
            ),
            None,
        )
        steam_id = next(
            (
                external.external_id
                for external in record.external_ids
                if external.provider == "steam"
            ),
            None,
        )
        try:
            if rawg_id:
                refreshed = await self._aggregator.get_game(rawg_id)
            elif steam_id:
                refreshed = await self._steam.get_game(steam_id)
            else:
                refreshed = None
        except GameProviderError as error:
            logger.warning("Could not refresh cached game id=%s: %s", game_id, error)
            return cached

        if refreshed is None:
            return cached
        refreshed.id = str(game_id)
        return await self._games.save(refreshed, synced_at=datetime.now(timezone.utc))

    async def get_reviews(
        self, game_id: int, *, limit: int = 20
    ) -> tuple[list[GameReview], int] | None:
        game = await self._games.get_by_id(game_id)
        if game is None:
            return None
        steam_id = game.external_ids.get("steam")
        if steam_id is None:
            return [], 0
        return await self._steam.get_reviews(steam_id, limit=limit)

    def _needs_refresh(self, last_synced_at: datetime | None) -> bool:
        if last_synced_at is None:
            return True
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last_synced_at).total_seconds()
        return age >= self._cache_ttl_seconds
