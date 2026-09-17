import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_session_factory
from app.providers import GameProviderError
from app.repositories import GameRepository
from app.schemas import Game, GameAchievement, GameReview, GameSummary
from app.services import GameService


class FakeAggregator:
    def __init__(self) -> None:
        self.search_result = [Game(title="Example", external_ids={"rawg": "1"})]
        self.details = Game(
            title="Example",
            description="Fresh description",
            external_ids={"rawg": "1", "steam": "2"},
        )
        self.fail_details = False
        self.detail_calls = 0

    async def search(self, query: str) -> list[Game]:
        return self.search_result

    async def get_game(self, external_id: str) -> Game | None:
        self.detail_calls += 1
        if self.fail_details:
            raise GameProviderError("upstream unavailable")
        return self.details


class FakeSteam:
    def __init__(self) -> None:
        self.review_calls = 0

    async def get_game(self, external_id: str) -> Game | None:
        return None

    async def get_reviews(self, external_id: str, *, limit: int):
        self.review_calls += 1
        return [GameReview(source="steam", text="Good", voted_up=True)], 1

    async def get_achievements(self, external_id: str):
        return [
            GameAchievement(name="WIN", display_name="Win", hidden=False),
        ]


class FakeAi:
    name = "fake-ai"
    model_name = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    async def summarize_reviews(self, game_title, reviews, *, language="ru"):
        self.calls += 1
        return GameSummary(
            summary=f"Summary for {game_title}",
            pros=["story"],
            cons=["performance"],
            sentiment={"positive": 0.8, "negative": 0.2, "neutral": 0},
            reviews_analyzed=len(reviews),
            model=self.model_name,
            source="steam",
            language=language,
        )


def test_service_search_persists_and_detail_refreshes_once() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        aggregator = FakeAggregator()
        try:
            async with factory() as session:
                service = GameService(
                    session, aggregator, FakeSteam(), cache_ttl_seconds=3600
                )
                results = await service.search_games("Example")
                assert results[0].id is not None
                details = await service.get_game(int(results[0].id))
                assert (
                    details is not None and details.description == "Fresh description"
                )
                assert aggregator.detail_calls == 1

                cached = await service.get_game(int(results[0].id))
                assert cached is not None and cached.description == "Fresh description"
                assert aggregator.detail_calls == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_service_returns_stale_data_when_refresh_fails() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        aggregator = FakeAggregator()
        aggregator.fail_details = True
        try:
            async with factory() as session:
                repository = GameRepository(session)
                saved = await repository.save(
                    Game(
                        title="Example",
                        description="Previously saved",
                        external_ids={"rawg": "1"},
                    ),
                    synced_at=datetime.now(timezone.utc) - timedelta(days=2),
                )
                service = GameService(
                    session, aggregator, FakeSteam(), cache_ttl_seconds=60
                )
                result = await service.get_game(int(saved.id))
                assert result is not None and result.description == "Previously saved"
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_service_fetches_steam_reviews_when_game_has_steam_id() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        steam = FakeSteam()
        try:
            async with factory() as session:
                repository = GameRepository(session)
                saved = await repository.save(
                    Game(title="Example", external_ids={"rawg": "1", "steam": "2"})
                )
                service = GameService(
                    session, FakeAggregator(), steam, cache_ttl_seconds=3600
                )
                result = await service.get_reviews(int(saved.id))
                assert result is not None and result[1] == 1
                assert steam.review_calls == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_service_fetches_steam_achievements_when_game_has_steam_id() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                repository = GameRepository(session)
                saved = await repository.save(
                    Game(title="Example", external_ids={"steam": "2"})
                )
                service = GameService(
                    session, FakeAggregator(), FakeSteam(), cache_ttl_seconds=3600
                )
                result = await service.get_achievements(int(saved.id))
                assert result is not None
                assert result[0].name == "WIN"
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_service_generates_and_reuses_cached_summary() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        ai = FakeAi()
        try:
            async with factory() as session:
                repository = GameRepository(session)
                saved = await repository.save(
                    Game(title="Example", external_ids={"steam": "2"})
                )
                service = GameService(
                    session,
                    FakeAggregator(),
                    FakeSteam(),
                    cache_ttl_seconds=3600,
                    ai_provider=ai,
                    ai_max_reviews=50,
                    ai_max_review_chars=2000,
                )
                first = await service.create_summary(int(saved.id))
                second = await service.create_summary(int(saved.id))
                latest = await service.get_summary(int(saved.id))
                assert first is not None and first.summary == "Summary for Example"
                assert second is not None and second.generated_at is not None
                assert latest is not None and latest.reviews_total == 1
                assert ai.calls == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_service_limits_total_review_prompt_size() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                service = GameService(
                    session,
                    FakeAggregator(),
                    FakeSteam(),
                    cache_ttl_seconds=3600,
                    ai_max_reviews=50,
                    ai_max_review_chars=2000,
                    ai_max_prompt_chars=2000,
                )
                reviews = [
                    GameReview(source="steam", text="x" * 1000, voted_up=True)
                    for _ in range(10)
                ]
                prepared = service._prepare_reviews(reviews)
                assert len(prepared) == 2
                assert sum(len(review.text) + 80 for review in prepared) <= 2000
        finally:
            await engine.dispose()

    asyncio.run(exercise())
