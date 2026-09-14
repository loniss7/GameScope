import asyncio
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_session_factory
from app.repositories import ExternalIdRepository, GameRepository, RatingRepository
from app.schemas import Game, GameRating


def test_game_repository_round_trip_and_preserve_existing_details() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        try:
            async with factory() as session:
                repository = GameRepository(session)
                game = Game(
                    title="Example Game",
                    description="Detailed description",
                    release_date=date(2024, 1, 2),
                    developers=["Studio"],
                    genres=["RPG"],
                    platforms=["PC"],
                    is_free=False,
                    achievement_count=42,
                    ratings=[GameRating(source="rawg", score=4, max_score=5)],
                    external_ids={"rawg": "123", "steam": "456"},
                )
                saved = await repository.save(
                    game, synced_at=datetime.now(timezone.utc)
                )
                await session.commit()

                minimal_search_result = Game(
                    title="Example Game",
                    external_ids={"rawg": "123"},
                )
                preserved = await repository.save(
                    minimal_search_result, preserve_existing=True
                )
                await session.commit()

                by_id = await repository.get_by_id(int(saved.id))
                by_external_id = await repository.get_by_external_id("steam", "456")
                local_search = await repository.search("Example")
                external_id_repo = ExternalIdRepository(session)
                rating_repo = RatingRepository(session)

                assert by_id is not None
                assert by_id.description == "Detailed description"
                assert by_id.release_date == date(2024, 1, 2)
                assert by_id.genres == ["RPG"]
                assert by_id.platforms == ["PC"]
                assert by_id.is_free is False
                assert by_id.achievement_count == 42
                assert by_id.id == saved.id == preserved.id
                assert by_external_id is not None and by_external_id.id == saved.id
                assert len(local_search) == 1
                assert await external_id_repo.get_game_id("rawg", "123") == int(
                    saved.id
                )
                assert len(await rating_repo.list_for_game(int(saved.id))) == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())
