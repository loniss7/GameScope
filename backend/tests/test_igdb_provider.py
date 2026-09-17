import asyncio
from datetime import date

import httpx
import pytest

from app.providers.igdb import IgdbProvider, IgdbProviderError, map_igdb_game


def _payload() -> dict:
    return {
        "id": 1942,
        "name": "The Witcher 3: Wild Hunt",
        "summary": "A story-driven role-playing game.",
        "first_release_date": 1431993600,
        "platforms": [{"id": 6, "name": "PC"}],
        "genres": [{"id": 12, "name": "Role-playing (RPG)"}],
        "game_modes": [{"id": 1, "name": "Single player"}],
        "involved_companies": [
            {
                "developer": True,
                "publisher": False,
                "company": {"id": 123, "name": "CD Projekt Red"},
            },
            {
                "developer": False,
                "publisher": True,
                "company": {"id": 456, "name": "CD Projekt"},
            },
        ],
        "cover": {"url": "//images.igdb.com/igdb/image/upload/t_cover/a.jpg"},
        "rating": 92.5,
        "rating_count": 1000,
        "aggregated_rating": 93.0,
        "aggregated_rating_count": 50,
        "external_games": [
            {"uid": "292030", "external_game_source": {"name": "Steam"}},
            {"uid": "gog-witcher-3", "external_game_source": {"name": "GOG"}},
        ],
    }


def test_map_igdb_game_to_shared_schema() -> None:
    game = map_igdb_game(_payload())

    assert game.title == "The Witcher 3: Wild Hunt"
    assert game.description == "A story-driven role-playing game."
    assert game.release_date == date(2015, 5, 19)
    assert game.developers == ["CD Projekt Red"]
    assert game.publishers == ["CD Projekt"]
    assert game.genres == ["Role-playing (RPG)"]
    assert game.categories == ["Single player"]
    assert game.platforms == ["PC"]
    assert game.image_url == "https://images.igdb.com/igdb/image/upload/t_cover/a.jpg"
    assert game.external_ids == {
        "igdb": "1942",
        "steam": "292030",
        "gog": "gog-witcher-3",
    }
    assert [(rating.source, rating.score) for rating in game.ratings] == [
        ("igdb", 92.5),
        ("igdb_critics", 93.0),
    ]


def test_provider_uses_twitch_token_and_apicalypse_body() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "auth.test":
            return httpx.Response(
                200, json={"access_token": "token-1", "expires_in": 3600}
            )
        assert request.url.path == "/v4/games"
        assert request.headers["Client-ID"] == "client-id"
        assert request.headers["Authorization"] == "Bearer token-1"
        body = request.content.decode()
        assert "fields id,name" in body
        assert 'search "The Witcher 3"' in body
        return httpx.Response(200, json=[_payload()])

    async def run() -> list:
        provider = IgdbProvider(
            "client-id",
            "client-secret",
            base_url="https://api.igdb.com/v4",
            auth_url="https://auth.test/oauth2/token",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await provider.search(" The Witcher 3 ")
        finally:
            await provider.aclose()

    games = asyncio.run(run())

    assert len(games) == 1
    assert games[0].external_ids["igdb"] == "1942"
    assert [request.url.host for request in requests] == ["auth.test", "api.igdb.com"]
    assert requests[0].url.params["client_id"] == "client-id"
    assert requests[0].url.params["grant_type"] == "client_credentials"


def test_provider_caches_token_between_requests() -> None:
    auth_requests = 0
    game_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_requests, game_requests
        if request.url.host == "auth.test":
            auth_requests += 1
            return httpx.Response(
                200, json={"access_token": "token-1", "expires_in": 3600}
            )
        game_requests += 1
        return httpx.Response(200, json=[_payload()])

    async def run() -> None:
        provider = IgdbProvider(
            "client-id",
            "client-secret",
            auth_url="https://auth.test/oauth2/token",
            transport=httpx.MockTransport(handler),
        )
        try:
            await provider.search("one")
            await provider.search("two")
        finally:
            await provider.aclose()

    asyncio.run(run())

    assert auth_requests == 1
    assert game_requests == 2


def test_provider_refreshes_token_after_unauthorized_response() -> None:
    auth_requests = 0
    game_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_requests, game_requests
        if request.url.host == "auth.test":
            auth_requests += 1
            return httpx.Response(
                200, json={"access_token": f"token-{auth_requests}", "expires_in": 3600}
            )
        game_requests += 1
        if game_requests == 1:
            return httpx.Response(401)
        return httpx.Response(200, json=[_payload()])

    async def run() -> list:
        provider = IgdbProvider(
            "client-id",
            "client-secret",
            auth_url="https://auth.test/oauth2/token",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await provider.search("one")
        finally:
            await provider.aclose()

    games = asyncio.run(run())

    assert len(games) == 1
    assert auth_requests == 2
    assert game_requests == 2


def test_provider_rejects_missing_credentials() -> None:
    with pytest.raises(ValueError, match="IGDB_CLIENT_ID"):
        IgdbProvider("", "secret")


def test_provider_raises_sanitized_error_for_invalid_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "auth.test":
            return httpx.Response(
                200, json={"access_token": "token-1", "expires_in": 3600}
            )
        return httpx.Response(200, json=[{"id": 1}])

    async def run() -> None:
        provider = IgdbProvider(
            "client-id",
            "client-secret",
            auth_url="https://auth.test/oauth2/token",
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(IgdbProviderError, match="invalid game search data"):
                await provider.search("one")
        finally:
            await provider.aclose()

    asyncio.run(run())
