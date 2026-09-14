import asyncio
from datetime import date

import httpx
import pytest

from app.providers.steam import SteamProvider, SteamProviderError, map_steam_game


def test_steam_mapper_normalizes_game_details() -> None:
    game = map_steam_game(
        "1091500",
        {
            "name": "Cyberpunk 2077",
            "about_the_game": "<p>Explore <strong>Night City</strong>.</p>",
            "release_date": {"date": "10 Dec, 2020"},
            "developers": ["CD PROJEKT RED"],
            "publishers": ["CD PROJEKT RED"],
            "genres": [{"description": "RPG"}],
            "categories": [{"description": "Single-player"}],
            "platforms": {"windows": True, "mac": False, "linux": False},
            "price_overview": {
                "currency": "USD",
                "final": 2999,
                "discount_percent": 50,
            },
            "is_free": False,
            "achievements": {"total": 44},
            "pc_requirements": {"minimum": "<strong>OS:</strong> Windows 10"},
            "header_image": "https://example.test/cyberpunk.jpg",
            "metacritic": {"score": 86},
        },
    )

    assert game.title == "Cyberpunk 2077"
    assert game.description == "Explore Night City."
    assert game.release_date == date(2020, 12, 10)
    assert game.genres == ["RPG"]
    assert game.categories == ["Single-player"]
    assert game.platforms == ["windows"]
    assert game.price is not None and str(game.price.amount) == "29.99"
    assert game.is_free is False
    assert game.achievement_count == 44
    assert game.system_requirements is not None
    assert game.system_requirements.minimum == "OS: Windows 10"
    assert game.ratings[0].source == "metacritic"
    assert game.external_ids == {"steam": "1091500"}


def test_search_and_get_game_map_steam_store_and_review_data() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith("storesearch/"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": 1091500,
                            "name": "Cyberpunk 2077",
                            "tiny_image": "https://example.test/cover.jpg",
                        }
                    ]
                },
            )
        if request.url.path.endswith("appdetails"):
            return httpx.Response(
                200,
                json={
                    "1091500": {
                        "success": True,
                        "data": {
                            "name": "Cyberpunk 2077",
                            "platforms": {"windows": True},
                        },
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "query_summary": {"total_reviews": 100, "total_positive": 80},
                "reviews": [
                    {
                        "author": {"steamid": "user-1", "playtime_forever": 900},
                        "language": "english",
                        "review": "Great story.",
                        "voted_up": True,
                        "timestamp_created": 1_700_000_000,
                    }
                ],
            },
        )

    async def exercise() -> tuple[list, object, tuple[list, int]]:
        provider = SteamProvider(transport=httpx.MockTransport(handler))
        try:
            return (
                await provider.search("Cyberpunk"),
                await provider.get_game("1091500"),
                await provider.get_reviews("1091500", limit=5),
            )
        finally:
            await provider.aclose()

    results, details, reviews = asyncio.run(exercise())
    assert results[0].external_ids == {"steam": "1091500"}
    assert details is not None
    assert details.ratings[0].source == "steam"
    assert details.ratings[0].score == 80
    assert reviews[1] == 100
    assert reviews[0][0].text == "Great story."
    assert reviews[0][0].created_at == date(2023, 11, 14)
    assert len(seen_paths) == 4


def test_steam_http_error_is_sanitized() -> None:
    async def exercise() -> None:
        provider = SteamProvider(
            transport=httpx.MockTransport(lambda _: httpx.Response(503))
        )
        try:
            with pytest.raises(SteamProviderError, match="HTTP 503"):
                await provider.search("Example")
        finally:
            await provider.aclose()

    asyncio.run(exercise())


def test_game_details_survive_when_steam_reviews_are_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("appdetails"):
            return httpx.Response(
                200,
                json={"42": {"success": True, "data": {"name": "Example Game"}}},
            )
        return httpx.Response(503)

    async def exercise():
        provider = SteamProvider(transport=httpx.MockTransport(handler))
        try:
            return await provider.get_game("42")
        finally:
            await provider.aclose()

    game = asyncio.run(exercise())
    assert game is not None
    assert game.title == "Example Game"
    assert game.ratings == []
