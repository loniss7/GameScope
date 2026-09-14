import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TypeVar

import httpx
import pytest
from pydantic import SecretStr

from app.providers.rawg import RawgProvider, RawgProviderError, map_rawg_game
from app.schemas import Game

Result = TypeVar("Result")


async def _call_provider(
    transport: httpx.AsyncBaseTransport,
    operation: Callable[[RawgProvider], Awaitable[Result]],
) -> Result:
    provider = RawgProvider(SecretStr("test-rawg-key"), transport=transport)
    try:
        return await operation(provider)
    finally:
        await provider.aclose()


def test_search_maps_rawg_fields_and_passes_api_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 123,
                        "name": "The Witcher 3: Wild Hunt",
                        "released": "2015-05-19",
                        "background_image": "https://example.test/witcher.jpg",
                        "rating": 4.5,
                        "rating_top": 4,
                        "ratings_count": 200,
                        "metacritic": 93,
                        "genres": [{"name": "RPG"}],
                        "platforms": [
                            {"platform": {"name": "PC"}},
                            {"platform": {"name": "PC"}},
                        ],
                        "developers": [{"name": "CD Projekt Red"}],
                        "publishers": [{"name": "CD Projekt"}],
                        "description_raw": "A story-driven role-playing game.",
                    }
                ]
            },
        )

    games = asyncio.run(
        _call_provider(
            httpx.MockTransport(handler),
            lambda provider: provider.search("  The Witcher 3  "),
        )
    )

    assert len(games) == 1
    game = games[0]
    assert game.title == "The Witcher 3: Wild Hunt"
    assert game.release_date == date(2015, 5, 19)
    assert game.platforms == ["PC"]
    assert game.genres == ["RPG"]
    assert game.developers == ["CD Projekt Red"]
    assert game.publishers == ["CD Projekt"]
    assert game.external_ids == {"rawg": "123"}
    assert game.id is None
    assert [rating.source for rating in game.ratings] == ["rawg", "metacritic"]
    assert game.ratings[0].max_score == 5

    assert len(requests) == 1
    assert requests[0].url.path == "/api/games"
    assert requests[0].url.params["search"] == "The Witcher 3"
    assert requests[0].url.params["page_size"] == "20"
    assert requests[0].url.params["key"] == "test-rawg-key"


def test_game_details_map_html_and_return_none_for_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/games/404"):
            return httpx.Response(404, json={"detail": "Not found"})
        return httpx.Response(
            200,
            json={
                "id": 456,
                "name": "Example Game",
                "description": "<p>A <strong>great</strong> game.</p>",
                "platforms": [{"platform": {"name": "PC"}}],
            },
        )

    async def fetch_details(provider: RawgProvider) -> tuple[Game | None, Game | None]:
        return await provider.get_game("456"), await provider.get_game("404")

    details, missing = asyncio.run(
        _call_provider(httpx.MockTransport(handler), fetch_details)
    )

    assert details is not None
    assert details.description == "A great game."
    assert details.external_ids == {"rawg": "456"}
    assert missing is None


def test_search_with_blank_query_does_not_call_rawg() -> None:
    def unexpected_request(_: httpx.Request) -> httpx.Response:
        pytest.fail("Blank queries must not make an HTTP request.")

    games = asyncio.run(
        _call_provider(
            httpx.MockTransport(unexpected_request),
            lambda provider: provider.search("   "),
        )
    )

    assert games == []


def test_http_errors_are_sanitized_and_do_not_expose_api_key() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "rate limited"})

    with pytest.raises(RawgProviderError, match="HTTP 429") as error:
        asyncio.run(
            _call_provider(
                httpx.MockTransport(handler),
                lambda provider: provider.search("Example"),
            )
        )

    assert "test-rawg-key" not in str(error.value)


def test_mapper_rejects_payload_without_required_fields() -> None:
    with pytest.raises(ValueError, match="id and a name"):
        map_rawg_game({"name": "Missing ID"})
