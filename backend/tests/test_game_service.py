import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_session_factory
from app.providers import GameProviderError
from app.repositories import GameRepository
from app.schemas import Game, GameReview
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
