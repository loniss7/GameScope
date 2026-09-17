import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.game import GameAggregator
from app.ai.base import AiProvider, AiProviderNotConfiguredError
from app.providers.base import GameProviderError
from app.providers.steam import SteamProvider
from app.repositories.games import GameRepository
from app.repositories.summaries import GameSummaryRepository
from app.schemas import Game, GameAchievement, GameReview, GameSummary

logger = logging.getLogger(__name__)


class SummaryUnavailableError(RuntimeError):
    """Raised when a game has no reviews that can be summarized."""


class GameService:
    """Use cases that coordinate providers, normalized data, and persistence."""

    def __init__(
        self,
        session: AsyncSession,
        aggregator: GameAggregator,
        steam_provider: SteamProvider,
        *,
        cache_ttl_seconds: int,
        ai_provider: AiProvider | None = None,
        ai_max_reviews: int = 10,
        ai_max_review_chars: int = 1000,
        ai_max_prompt_chars: int = 12000,
    ) -> None:
        self._games = GameRepository(session)
        self._summaries = GameSummaryRepository(session)
        self._aggregator = aggregator
        self._steam = steam_provider
        self._ai = ai_provider
        self._cache_ttl_seconds = cache_ttl_seconds
        self._ai_max_reviews = max(1, min(ai_max_reviews, 100))
        self._ai_max_review_chars = max(200, min(ai_max_review_chars, 10000))
        self._ai_max_prompt_chars = max(2000, min(ai_max_prompt_chars, 100000))

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

    async def get_achievements(self, game_id: int) -> list[GameAchievement] | None:
        game = await self._games.get_by_id(game_id)
        if game is None:
            return None
        steam_id = game.external_ids.get("steam")
        if steam_id is None:
            return []
        return await self._steam.get_achievements(steam_id)

    async def get_summary(self, game_id: int) -> GameSummary | None:
        return await self._summaries.get_latest(game_id)

    async def create_summary(
        self,
        game_id: int,
        *,
        language: str = "ru",
        force_refresh: bool = False,
    ) -> GameSummary | None:
        game = await self._games.get_by_id(game_id)
        if game is None:
            return None
        if self._ai is None:
            raise AiProviderNotConfiguredError("AI provider is not configured.")

        steam_id = game.external_ids.get("steam")
        if steam_id is None:
            raise SummaryUnavailableError(
                "Steam reviews are unavailable for this game."
            )

        reviews, total = await self._steam.get_reviews(
            steam_id, limit=self._ai_max_reviews
        )
        prepared_reviews = self._prepare_reviews(reviews)
        if not prepared_reviews:
            raise SummaryUnavailableError(
                "No Steam reviews are available to summarize."
            )

        normalized_language = language.strip().lower() or "ru"
        reviews_hash = self._reviews_hash(prepared_reviews, total)
        model_name = getattr(self._ai, "model_name", self._ai.name)
        if not force_refresh:
            cached = await self._summaries.get_by_snapshot(
                game_id,
                source="steam",
                model=model_name,
                language=normalized_language,
                reviews_hash=reviews_hash,
            )
            if cached is not None:
                return cached

        summary = await self._ai.summarize_reviews(
            game.title,
            prepared_reviews,
            language=normalized_language,
        )
        summary = summary.model_copy(
            update={
                "source": "steam",
                "language": normalized_language,
                "reviews_analyzed": len(prepared_reviews),
                "reviews_total": total,
                "generated_at": datetime.now(timezone.utc),
            }
        )
        return await self._summaries.save(
            game_id,
            summary,
            reviews_hash=reviews_hash,
        )

    def _prepare_reviews(self, reviews: list[GameReview]) -> list[GameReview]:
        prepared: list[GameReview] = []
        # A model's context is shared by the system prompt, game metadata and
        # every review.  Limit the combined review text so a local model does
        # not reject the request or spend minutes processing an oversized
        # prompt even when AI_MAX_REVIEWS is configured to a large value.
        prompt_chars = 0
        review_overhead = 80
        for review in reviews[: self._ai_max_reviews]:
            text = re.sub(r"\s+", " ", review.text).strip()
            if not text:
                continue
            remaining = self._ai_max_prompt_chars - prompt_chars - review_overhead
            if remaining <= 0:
                break
            clipped = text[: min(self._ai_max_review_chars, remaining)]
            if not clipped:
                break
            prepared.append(review.model_copy(update={"text": clipped}))
            # Account for the review label and a newline in the generated
            # prompt.  This keeps the total below the configured budget.
            prompt_chars += len(clipped) + review_overhead
        return prepared

    @staticmethod
    def _reviews_hash(reviews: list[GameReview], total: int) -> str:
        payload = {
            "total": total,
            "reviews": [review.model_dump(mode="json") for review in reviews],
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _needs_refresh(self, last_synced_at: datetime | None) -> bool:
        if last_synced_at is None:
            return True
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last_synced_at).total_seconds()
        return age >= self._cache_ttl_seconds
