import logging
import re
from datetime import date
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import SecretStr, ValidationError

from app.providers.base import GameProvider, GameProviderError
from app.schemas import Game, GameRating

logger = logging.getLogger(__name__)

RAWG_API_BASE_URL = "https://api.rawg.io/api/"
RAWG_PAGE_SIZE = 20
RAWG_RATING_MAX = 5.0


class RawgProviderError(GameProviderError):
    """A sanitized error raised for RAWG network or response failures."""


class _HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    parser = _HtmlTextParser()
    parser.feed(value)
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return text or None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _names(values: Any, *, nested_key: str | None = None) -> list[str]:
    if not isinstance(values, list):
        return []

    result: list[str] = []
    for item in values:
        value = item.get(nested_key) if isinstance(item, dict) and nested_key else item
        if isinstance(value, dict):
            value = value.get("name")
        if isinstance(value, str) and value.strip() and value.strip() not in result:
            result.append(value.strip())
    return result


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def map_rawg_game(payload: dict[str, Any]) -> Game:
    """Convert a RAWG game object into the provider-independent Game schema."""
    rawg_id = payload.get("id")
    title = payload.get("name")
    if (
        isinstance(rawg_id, bool)
        or not isinstance(rawg_id, (int, str))
        or not str(rawg_id).strip()
        or not isinstance(title, str)
        or not title.strip()
    ):
        raise ValueError("RAWG game payload must include an id and a name.")

    ratings: list[GameRating] = []
    rating = payload.get("rating")
    if _is_number(rating):
        ratings_count = payload.get("ratings_count")
        if (
            not isinstance(ratings_count, int)
            or isinstance(ratings_count, bool)
            or ratings_count < 0
        ):
            ratings_count = None
        ratings.append(
            GameRating(
                source="rawg",
                score=float(rating),
                max_score=RAWG_RATING_MAX,
                rating_count=ratings_count,
            )
        )

    metacritic = payload.get("metacritic")
    if _is_number(metacritic) and 0 <= metacritic <= 100:
        ratings.append(
            GameRating(source="metacritic", score=float(metacritic), max_score=100)
        )

    try:
        return Game(
            title=title,
            description=_plain_text(
                payload.get("description_raw") or payload.get("description")
            ),
            release_date=_parse_date(payload.get("released")),
            developers=_names(payload.get("developers")),
            publishers=_names(payload.get("publishers")),
            genres=_names(payload.get("genres")),
            platforms=_names(payload.get("platforms"), nested_key="platform"),
            ratings=ratings,
            image_url=(
                payload.get("background_image")
                if isinstance(payload.get("background_image"), str)
                else None
            ),
            external_ids={"rawg": str(rawg_id)},
        )
    except ValidationError as error:
        raise ValueError("RAWG game payload contains invalid game data.") from error


class RawgProvider(GameProvider):
    """RAWG API adapter that returns normalized Game models."""

    name = "rawg"

    def __init__(
        self,
        api_key: SecretStr | str | None,
        *,
        base_url: str = RAWG_API_BASE_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                "RAWG_API_KEY must be configured before using RawgProvider."
            )

        self._api_key = key.strip()
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=timeout_seconds,
            transport=transport,
        )

    async def search(self, query: str) -> list[Game]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        payload = await self._get_json(
            "games",
            params={"search": normalized_query, "page_size": RAWG_PAGE_SIZE},
        )
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise RawgProviderError("RAWG returned an invalid game search response.")

        games: list[Game] = []
        for raw_game in raw_results:
            if not isinstance(raw_game, dict):
                continue
            try:
                games.append(map_rawg_game(raw_game))
            except ValueError:
                logger.warning("Skipping a malformed game in RAWG search results.")
        return games

    async def get_game(self, external_id: str) -> Game | None:
        normalized_id = external_id.strip()
        if not normalized_id:
            return None

        payload = await self._get_json(
            f"games/{quote(normalized_id, safe='')}",
            not_found_is_empty=True,
        )
        if payload is None:
            return None
        try:
            return map_rawg_game(payload)
        except ValueError:
            raise RawgProviderError("RAWG returned invalid game details.") from None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        not_found_is_empty: bool = False,
    ) -> dict[str, Any] | None:
        try:
            response = await self._client.get(
                path,
                params={"key": self._api_key, **(params or {})},
            )
        except httpx.RequestError:
            raise RawgProviderError(
                "Could not complete the RAWG API request."
            ) from None

        if response.status_code == 404 and not_found_is_empty:
            return None
        if not 200 <= response.status_code < 300:
            raise RawgProviderError(f"RAWG returned HTTP {response.status_code}.")

        try:
            payload = response.json()
        except ValueError:
            raise RawgProviderError("RAWG returned invalid JSON.") from None
        if not isinstance(payload, dict):
            raise RawgProviderError("RAWG returned an invalid response body.")
        return payload
