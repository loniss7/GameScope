from fastapi.testclient import TestClient

from app.ai.base import AiProviderNotConfiguredError
from app.api.dependencies import get_game_service
from app.main import create_app
from app.providers.base import GameProviderError
from app.schemas import Game, GameAchievement, GameReview, GameSummary


class FakeGameService:
    async def search_games(self, query: str, *, limit: int = 20) -> list[Game]:
        return [Game(id="123", title=query, external_ids={"rawg": "rawg-1"})]

    async def get_game(self, game_id: int) -> Game | None:
        return Game(id=str(game_id), title="Example Game") if game_id == 123 else None

    async def get_reviews(self, game_id: int, *, limit: int = 20):
        if game_id != 123:
            return None
        return [GameReview(source="steam", text="Good", voted_up=True)], 1

    async def get_achievements(self, game_id: int):
        if game_id != 123:
            return None
        return [GameAchievement(name="WIN", display_name="Win")]

    async def get_summary(self, game_id: int):
        if game_id != 123:
            return None
        return GameSummary(
            summary="Good game.",
            sentiment={"positive": 1, "negative": 0, "neutral": 0},
            reviews_analyzed=1,
            reviews_total=1,
            model="test-model",
            source="steam",
        )

    async def create_summary(self, game_id: int, *, language: str, force_refresh: bool):
        return await self.get_summary(game_id)


def test_search_detail_and_reviews_routes_return_normalized_data() -> None:
    app = create_app()
    app.dependency_overrides[get_game_service] = lambda: FakeGameService()
    try:
        with TestClient(app) as client:
            search = client.get("/api/games/search", params={"q": "Example"})
            details = client.get("/api/games/123")
            reviews = client.get("/api/games/123/reviews")
            achievements = client.get("/api/games/123/achievements")
            summary = client.get("/api/games/123/summary")
            generated = client.post("/api/games/123/summary", params={"language": "ru"})
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
    assert achievements.status_code == 200
    assert achievements.json()["items"][0]["name"] == "WIN"
    assert achievements.json()["total"] == 1
    assert summary.status_code == 200
    assert summary.json()["summary"] == "Good game."
    assert generated.status_code == 200
    assert generated.json()["model"] == "test-model"
    assert missing.status_code == 404


def test_summary_api_reports_unavailable_ai_provider() -> None:
    class UnavailableService:
        async def create_summary(
            self, game_id: int, *, language: str, force_refresh: bool
        ):
            raise AiProviderNotConfiguredError("AI provider is not configured.")

    app = create_app()
    app.dependency_overrides[get_game_service] = lambda: UnavailableService()
    try:
        with TestClient(app) as client:
            response = client.post("/api/games/123/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ai_provider_unavailable"


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
