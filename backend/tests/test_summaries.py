import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_session_factory
from app.repositories.games import GameRepository
from app.repositories.summaries import GameSummaryRepository
from app.schemas import Game, GameSummary


def test_summary_repository_round_trip_and_snapshot_lookup() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                game = await GameRepository(session).save(
                    Game(title="Example", external_ids={"steam": "42"})
                )
                summary = GameSummary(
                    summary="Mostly positive.",
                    pros=["story"],
                    cons=["performance"],
                    sentiment={"positive": 0.8, "negative": 0.2, "neutral": 0},
                    reviews_analyzed=2,
                    reviews_total=10,
                    model="qwen3:8b",
                    source="steam",
                    language="ru",
                    generated_at=datetime.now(timezone.utc),
                )
                repository = GameSummaryRepository(session)
                saved = await repository.save(
                    int(game.id), summary, reviews_hash="a" * 64
                )
                await session.commit()

                latest = await repository.get_latest(int(game.id))
                by_snapshot = await repository.get_by_snapshot(
                    int(game.id),
                    source="steam",
                    model="qwen3:8b",
                    language="ru",
                    reviews_hash="a" * 64,
                )
                assert saved.summary == "Mostly positive."
                assert latest is not None and latest.pros == ["story"]
                assert by_snapshot is not None and by_snapshot.reviews_total == 10
        finally:
            await engine.dispose()

    asyncio.run(exercise())
