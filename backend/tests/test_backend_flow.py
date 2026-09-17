import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.main import create_app
from app.schemas import Game, GameReview


class StubAggregator:
    async def search(self, query: str) -> list[Game]:
        return [Game(title="Example Game", external_ids={"rawg": "rawg-42"})]

    async def get_game(self, external_id: str) -> Game:
        return Game(
            title="Example Game",
            description="Combined details",
            external_ids={"rawg": external_id, "steam": "steam-42"},
        )


class StubSteam:
    async def get_reviews(self, external_id: str, *, limit: int):
        return [GameReview(source="steam", text="Works well", voted_up=True)], 1


def test_http_flow_searches_persists_fetches_details_and_reviews() -> None:
    database_path = Path(__file__).with_name(f".api-flow-{uuid4().hex}.db").resolve()
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"

    async def create_schema() -> None:
        engine = create_async_engine(database_url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    try:
        asyncio.run(create_schema())
        settings = Settings(
            _env_file=None,
            rawg_api_key=SecretStr("test-key"),
            database_url=database_url,
        )
        app = create_app(settings)
        with TestClient(app) as client:
            app.state.game_aggregator = StubAggregator()
            app.state.steam_provider = StubSteam()
            search = client.get("/api/games/search", params={"q": "Example"})
            game_id = search.json()["items"][0]["id"]
            details = client.get(f"/api/games/{game_id}")
            reviews = client.get(f"/api/games/{game_id}/reviews")
    finally:
        database_path.unlink(missing_ok=True)

    assert search.status_code == 200
    assert isinstance(game_id, str) and game_id.isdigit()
    assert details.status_code == 200
    assert details.json()["description"] == "Combined details"
    assert details.json()["external_ids"]["steam"] == "steam-42"
    assert reviews.status_code == 200
    assert reviews.json()["items"][0]["text"] == "Works well"
