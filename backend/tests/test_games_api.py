from fastapi.testclient import TestClient

from app.api.dependencies import get_game_service
from app.main import create_app
from app.providers.base import GameProviderError
from app.schemas import Game, GameReview


class FakeGameService:
    async def search_games(self, query: str, *, limit: int = 20) -> list[Game]:
        return [Game(id="123", title=query, external_ids={"rawg": "rawg-1"})]

    async def get_game(self, game_id: int) -> Game | None:
        return Game(id=str(game_id), title="Example Game") if game_id == 123 else None

    async def get_reviews(self, game_id: int, *, limit: int = 20):
        if game_id != 123:
            return None
        return [GameReview(source="steam", text="Good", voted_up=True)], 1


def test_search_detail_and_reviews_routes_return_normalized_data() -> None:
    app = create_app()
    app.dependency_overrides[get_game_service] = lambda: FakeGameService()
    try:
        with TestClient(app) as client:
            search = client.get("/api/games/search", params={"q": "Example"})
            details = client.get("/api/games/123")
            reviews = client.get("/api/games/123/reviews")
            missing = client.get("/api/games/999")
    finally:
        app.dependency_overrides.clear()

    assert search.status_code == 200
    assert search.json()["items"][0]["id"] == "123"
    assert details.status_code == 200
    assert details.json()["title"] == "Example Game"
    assert reviews.status_code == 200
    assert reviews.json()["items"][0]["source"] == "steam"
    assert reviews.json()["total"] == 1
    assert missing.status_code == 404


def test_search_api_validates_query_and_reports_upstream_failure() -> None:
    class FailedService(FakeGameService):
        async def search_games(self, query: str, *, limit: int = 20) -> list[Game]:
            raise GameProviderError("RAWG returned HTTP 429.")

    app = create_app()
    app.dependency_overrides[get_game_service] = lambda: FailedService()
    try:
        with TestClient(app) as client:
            invalid = client.get("/api/games/search", params={"q": " "})
            failed = client.get("/api/games/search", params={"q": "Example"})
    finally:
        app.dependency_overrides.clear()

    assert invalid.status_code == 422
    assert failed.status_code == 502
    assert failed.json()["detail"]["code"] == "provider_error"
