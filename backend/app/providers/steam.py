import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from time import strptime
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.providers.base import GameProvider, GameProviderError
from app.schemas import (
    Game,
    GamePrice,
    GameRating,
    GameReview,
    GameSystemRequirements,
)

logger = logging.getLogger(__name__)

STEAM_STORE_BASE_URL = "https://store.steampowered.com/"
STEAM_POSITIVE_RATING_MAX = 100.0


class SteamProviderError(GameProviderError):
    """A sanitized error raised for Steam network or response failures."""


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parser = _TextParser()
    parser.feed(value)
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text or None


def _parse_release_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    for pattern in ("%d %b, %Y", "%b %d, %Y", "%B %d, %Y", "%d %B, %Y"):
        try:
            parsed = strptime(raw, pattern)
            return date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday)
        except ValueError:
            continue
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        name = item.get("description") if isinstance(item, dict) else item
        if isinstance(name, str) and name.strip():
            cleaned = name.strip()
            if cleaned.casefold() not in {existing.casefold() for existing in result}:
                result.append(cleaned)
    return result


def _system_requirements(value: Any) -> GameSystemRequirements | None:
    if not isinstance(value, dict):
        return None
    minimum = _plain_text(value.get("minimum"))
    recommended = _plain_text(value.get("recommended"))
    if minimum is None and recommended is None:
        return None
    return GameSystemRequirements(minimum=minimum, recommended=recommended)


def map_steam_game(app_id: str, payload: dict[str, Any]) -> Game:
    """Map Steam Store app-details payload into the shared Game schema."""
    title = payload.get("name")
    if not app_id.isdigit() or not isinstance(title, str) or not title.strip():
        raise ValueError("Steam game payload must include a numeric id and a name.")

    platforms_payload = payload.get("platforms")
    platforms = (
        [name for name, enabled in platforms_payload.items() if enabled is True]
        if isinstance(platforms_payload, dict)
        else []
    )
    price_payload = payload.get("price_overview")
    price = None
    if isinstance(price_payload, dict):
        final = price_payload.get("final")
        currency = price_payload.get("currency")
        if (
            isinstance(final, int)
            and final >= 0
            and isinstance(currency, str)
            and currency
        ):
            discount = price_payload.get("discount_percent", 0)
            if not isinstance(discount, int) or isinstance(discount, bool):
                discount = 0
            price = GamePrice(
                amount=Decimal(final) / Decimal(100),
                currency=currency,
                discount_percent=max(0, min(discount, 100)),
            )

    is_free = (
        payload.get("is_free") if isinstance(payload.get("is_free"), bool) else None
    )
    achievements_payload = payload.get("achievements")
    achievement_count = (
        achievements_payload.get("total")
        if isinstance(achievements_payload, dict)
        else None
    )
    if (
        not isinstance(achievement_count, int)
        or isinstance(achievement_count, bool)
        or achievement_count < 0
    ):
        achievement_count = None

    requirements = _system_requirements(payload.get("pc_requirements"))
    release = payload.get("release_date")
    release_value = release.get("date") if isinstance(release, dict) else None
    metacritic = payload.get("metacritic")
    ratings: list[GameRating] = []
    if isinstance(metacritic, dict):
        score = metacritic.get("score")
        if isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 100:
            ratings.append(GameRating(source="metacritic", score=score, max_score=100))

    try:
        return Game(
            title=title.strip(),
            description=_plain_text(
                payload.get("about_the_game") or payload.get("short_description")
            ),
            release_date=_parse_release_date(release_value),
            developers=_string_list(payload.get("developers")),
            publishers=_string_list(payload.get("publishers")),
            genres=_string_list(payload.get("genres")),
            categories=_string_list(payload.get("categories")),
            platforms=platforms,
            ratings=ratings,
            price=price,
            is_free=is_free,
            achievement_count=achievement_count,
            system_requirements=requirements,
            image_url=(
                payload.get("header_image")
                if isinstance(payload.get("header_image"), str)
                else None
            ),
            external_ids={"steam": app_id},
        )
    except ValidationError as error:
        raise ValueError("Steam game payload contains invalid game data.") from error


class SteamProvider(GameProvider):
    """Steam Store adapter. Steam's public store endpoints do not require a key."""

    name = "steam"

    def __init__(
        self,
        *,
        base_url: str = STEAM_STORE_BASE_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": "GameScope/0.1"},
        )

    async def search(self, query: str) -> list[Game]:
        normalized_query = query.strip()
        if not normalized_query:
            return []
        payload = await self._get_json(
            "api/storesearch/",
            params={"term": normalized_query, "l": "en", "cc": "US"},
        )
        items = payload.get("items")
        if not isinstance(items, list):
            raise SteamProviderError("Steam returned an invalid game search response.")

        games: list[Game] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            app_id = item.get("id")
            title = item.get("name")
            if (
                isinstance(app_id, int)
                and not isinstance(app_id, bool)
                and isinstance(title, str)
                and title.strip()
            ):
                games.append(
                    Game(
                        title=title.strip(),
                        image_url=item.get("tiny_image")
                        if isinstance(item.get("tiny_image"), str)
                        else None,
                        external_ids={"steam": str(app_id)},
                    )
                )
        return games

    async def get_game(self, external_id: str) -> Game | None:
        app_id = external_id.strip()
        if not app_id.isdigit():
            return None
        payload = await self._get_json(
            "api/appdetails", params={"appids": app_id, "cc": "US", "l": "en"}
        )
        app_data = payload.get(app_id)
        if not isinstance(app_data, dict):
            raise SteamProviderError("Steam returned invalid game details.")
        if app_data.get("success") is not True:
            return None
        details = app_data.get("data")
        if not isinstance(details, dict):
            raise SteamProviderError("Steam returned invalid game details.")
        try:
            game = map_steam_game(app_id, details)
        except ValueError:
            raise SteamProviderError("Steam returned invalid game details.") from None

        try:
            review_data = await self._get_reviews_payload(app_id, limit=1)
        except SteamProviderError as error:
            logger.warning(
                "Steam review summary unavailable for app id=%s: %s", app_id, error
            )
            return game
        summary = review_data.get("query_summary")
        if isinstance(summary, dict):
            total = summary.get("total_reviews")
            positive = summary.get("total_positive")
            if (
                isinstance(total, int)
                and total > 0
                and isinstance(positive, int)
                and 0 <= positive <= total
            ):
                game.ratings.append(
                    GameRating(
                        source="steam",
                        score=round(positive / total * STEAM_POSITIVE_RATING_MAX, 2),
                        max_score=STEAM_POSITIVE_RATING_MAX,
                        rating_count=total,
                    )
                )
        return game

    async def get_reviews(
        self, external_id: str, *, limit: int = 20
    ) -> tuple[list[GameReview], int]:
        app_id = external_id.strip()
        if not app_id.isdigit():
            return [], 0
        normalized_limit = max(1, min(limit, 100))
        payload = await self._get_reviews_payload(app_id, limit=normalized_limit)
        raw_reviews = payload.get("reviews")
        summary = payload.get("query_summary")
        total = summary.get("total_reviews", 0) if isinstance(summary, dict) else 0
        if not isinstance(total, int) or total < 0:
            total = 0
        if not isinstance(raw_reviews, list):
            raise SteamProviderError("Steam returned an invalid reviews response.")

        reviews: list[GameReview] = []
        for item in raw_reviews:
            if not isinstance(item, dict):
                continue
            author_data = item.get("author")
            author = (
                author_data.get("steamid") if isinstance(author_data, dict) else None
            )
            playtime = (
                author_data.get("playtime_forever")
                if isinstance(author_data, dict)
                else None
            )
            created = item.get("timestamp_created")
            try:
                created_at = (
                    datetime.fromtimestamp(created, tz=timezone.utc).date()
                    if isinstance(created, int) and created >= 0
                    else None
                )
            except (OverflowError, OSError, ValueError):
                created_at = None
            review_text = item.get("review")
            voted_up = item.get("voted_up")
            if not isinstance(review_text, str) or not isinstance(voted_up, bool):
                continue
            reviews.append(
                GameReview(
                    source="steam",
                    author=str(author) if author is not None else None,
                    language=item.get("language")
                    if isinstance(item.get("language"), str)
                    else None,
                    text=review_text,
                    voted_up=voted_up,
                    created_at=created_at,
                    playtime_minutes=playtime
                    if isinstance(playtime, int) and playtime >= 0
                    else None,
                )
            )
        return reviews, total

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_reviews_payload(self, app_id: str, *, limit: int) -> dict[str, Any]:
        return await self._get_json(
            f"appreviews/{quote(app_id, safe='')}",
            params={
                "json": 1,
                "num_per_page": limit,
                "language": "all",
                "purchase_type": "all",
            },
        )

    async def _get_json(
        self, path: str, *, params: dict[str, str | int]
    ) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
        except httpx.RequestError:
            raise SteamProviderError(
                "Could not complete the Steam API request."
            ) from None
        if not 200 <= response.status_code < 300:
            raise SteamProviderError(f"Steam returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError:
            raise SteamProviderError("Steam returned invalid JSON.") from None
        if not isinstance(payload, dict):
            raise SteamProviderError("Steam returned an invalid response body.")
        return payload
