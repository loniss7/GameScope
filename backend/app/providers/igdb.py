"""IGDB provider and Twitch OAuth token management."""

import asyncio
import re
import time
from collections import deque
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import SecretStr, ValidationError

from app.providers.base import GameProvider, GameProviderError
from app.schemas import Game, GameRating

IGDB_API_BASE_URL = "https://api.igdb.com/v4"
IGDB_AUTH_URL = "https://id.twitch.tv/oauth2/token"
IGDB_PAGE_SIZE = 20
IGDB_RATING_MAX = 100.0
IGDB_MAX_RETRIES = 2


class IgdbProviderError(GameProviderError):
    """A sanitized error raised for IGDB network or response failures."""


class IgdbAuthenticationError(IgdbProviderError):
    """Raised when Twitch credentials cannot produce an IGDB token."""


class _RequestLimiter:
    """Bound requests by both IGDB's RPS and concurrent request limits."""

    def __init__(self, requests_per_second: int, max_concurrency: int) -> None:
        self._rate = max(1, min(requests_per_second, 4))
        self._semaphore = asyncio.Semaphore(max(1, min(max_concurrency, 8)))
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        try:
            while True:
                async with self._lock:
                    now = time.monotonic()
                    while self._timestamps and now - self._timestamps[0] >= 1.0:
                        self._timestamps.popleft()
                    if len(self._timestamps) < self._rate:
                        self._timestamps.append(now)
                        return
                    wait_seconds = max(0.01, 1.0 - (now - self._timestamps[0]))
                await asyncio.sleep(wait_seconds)
        except BaseException:
            self._semaphore.release()
            raise

    def release(self) -> None:
        self._semaphore.release()


class IgdbTokenManager:
    """Fetch and cache Twitch client-credentials tokens for IGDB requests."""

    def __init__(
        self,
        client_id: SecretStr | str,
        client_secret: SecretStr | str,
        *,
        auth_url: str = IGDB_AUTH_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client_id = self._secret_value(client_id)
        self._client_secret = self._secret_value(client_secret)
        if not self._client_id or not self._client_secret:
            raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET are required.")
        self._auth_url = auth_url
        self._client = httpx.AsyncClient(timeout=timeout_seconds, transport=transport)
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        now = time.monotonic()
        if self._token is not None and now < self._expires_at:
            return self._token

        async with self._lock:
            now = time.monotonic()
            if self._token is not None and now < self._expires_at:
                return self._token
            try:
                response = await self._client.post(
                    self._auth_url,
                    params={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "client_credentials",
                    },
                )
            except httpx.RequestError:
                raise IgdbAuthenticationError(
                    "Could not connect to the Twitch OAuth service."
                ) from None
            if not 200 <= response.status_code < 300:
                raise IgdbAuthenticationError(
                    f"Twitch OAuth returned HTTP {response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError:
                raise IgdbAuthenticationError(
                    "Twitch OAuth returned invalid JSON."
                ) from None
            token = payload.get("access_token") if isinstance(payload, dict) else None
            expires_in = payload.get("expires_in") if isinstance(payload, dict) else 0
            if (
                not isinstance(token, str)
                or not token.strip()
                or not isinstance(expires_in, (int, float))
                or isinstance(expires_in, bool)
                or expires_in <= 0
            ):
                raise IgdbAuthenticationError(
                    "Twitch OAuth returned an invalid access token."
                )
            self._token = token.strip()
            self._expires_at = time.monotonic() + max(0.0, float(expires_in) - 60.0)
            return self._token

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0

    @property
    def client_id(self) -> str:
        return self._client_id

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _secret_value(value: SecretStr | str) -> str:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return raw.strip() if isinstance(raw, str) else ""


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        name = item.get("name") if isinstance(item, dict) else item
        if isinstance(name, str) and name.strip():
            cleaned = name.strip()
            if cleaned.casefold() not in {existing.casefold() for existing in result}:
                result.append(cleaned)
    return result


def _plain_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _release_date(value: Any) -> date | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).date()
    except (OverflowError, OSError, ValueError):
        return None


def _image_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    url = value.strip()
    return f"https:{url}" if url.startswith("//") else url


def _company_names(payload: Any) -> tuple[list[str], list[str]]:
    if not isinstance(payload, list):
        return [], []
    developers: list[str] = []
    publishers: list[str] = []
    for relation in payload:
        if not isinstance(relation, dict):
            continue
        company = relation.get("company")
        name = company.get("name") if isinstance(company, dict) else company
        if not isinstance(name, str) or not name.strip():
            continue
        cleaned = name.strip()
        if relation.get("developer") is True and cleaned.casefold() not in {
            value.casefold() for value in developers
        }:
            developers.append(cleaned)
        if relation.get("publisher") is True and cleaned.casefold() not in {
            value.casefold() for value in publishers
        }:
            publishers.append(cleaned)
    return developers, publishers


_EXTERNAL_SOURCE_IDS = {
    1: "steam",
    5: "gog",
    10: "youtube",
    11: "microsoft",
    26: "epic",
    28: "oculus",
    30: "itch_io",
    31: "xbox",
    36: "playstation",
}


def _external_ids(payload: Any, igdb_id: int | str) -> dict[str, str]:
    result = {"igdb": str(igdb_id)}
    if not isinstance(payload, list):
        return result
    for item in payload:
        if not isinstance(item, dict):
            continue
        uid = item.get("uid")
        if not isinstance(uid, (str, int)) or isinstance(uid, bool) or not str(uid):
            continue
        source = item.get("external_game_source")
        if isinstance(source, dict):
            source = source.get("name")
        if isinstance(source, str):
            normalized_source = source.strip().casefold().replace(" ", "_")
        elif isinstance(source, int) and not isinstance(source, bool):
            normalized_source = _EXTERNAL_SOURCE_IDS.get(source, "")
        else:
            normalized_source = ""
        if normalized_source in {
            "steam",
            "gog",
            "epic",
            "xbox",
            "playstation",
            "microsoft",
            "itch_io",
        }:
            result.setdefault(normalized_source, str(uid))
    return result


def map_igdb_game(payload: dict[str, Any]) -> Game:
    """Convert an IGDB game object into the provider-independent Game schema."""
    igdb_id = payload.get("id")
    title = payload.get("name")
    if (
        isinstance(igdb_id, bool)
        or not isinstance(igdb_id, (int, str))
        or not str(igdb_id).strip()
        or not isinstance(title, str)
        or not title.strip()
    ):
        raise ValueError("IGDB game payload must include an id and a name.")

    ratings: list[GameRating] = []
    user_rating = _number(payload.get("rating"))
    user_count = _non_negative_int(payload.get("rating_count"))
    if user_rating is not None and 0 <= user_rating <= IGDB_RATING_MAX:
        ratings.append(
            GameRating(
                source="igdb",
                score=user_rating,
                max_score=IGDB_RATING_MAX,
                rating_count=user_count,
            )
        )
    critics_rating = _number(payload.get("aggregated_rating"))
    critics_count = _non_negative_int(payload.get("aggregated_rating_count"))
    if critics_rating is not None and 0 <= critics_rating <= IGDB_RATING_MAX:
        ratings.append(
            GameRating(
                source="igdb_critics",
                score=critics_rating,
                max_score=IGDB_RATING_MAX,
                rating_count=critics_count,
            )
        )

    developers, publishers = _company_names(payload.get("involved_companies"))
    platforms = _names(payload.get("platforms"))
    genres = _names(payload.get("genres"))
    game_modes = _names(payload.get("game_modes"))
    cover = payload.get("cover")
    cover_url = cover.get("url") if isinstance(cover, dict) else cover

    try:
        return Game(
            title=title.strip(),
            description=_plain_text(payload.get("summary") or payload.get("storyline")),
            release_date=_release_date(payload.get("first_release_date")),
            developers=developers,
            publishers=publishers,
            genres=genres,
            categories=game_modes,
            platforms=platforms,
            ratings=ratings,
            image_url=_image_url(cover_url),
            external_ids=_external_ids(payload.get("external_games"), igdb_id),
        )
    except ValidationError as error:
        raise ValueError("IGDB game payload contains invalid game data.") from error


class IgdbProvider(GameProvider):
    """IGDB adapter using Twitch client-credentials authentication."""

    name = "igdb"

    def __init__(
        self,
        client_id: SecretStr | str,
        client_secret: SecretStr | str,
        *,
        base_url: str = IGDB_API_BASE_URL,
        auth_url: str = IGDB_AUTH_URL,
        timeout_seconds: float = 10.0,
        requests_per_second: int = 4,
        max_concurrency: int = 8,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=timeout_seconds,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "GameScope/0.1"},
        )
        self._token_manager = IgdbTokenManager(
            client_id,
            client_secret,
            auth_url=auth_url,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._limiter = _RequestLimiter(requests_per_second, max_concurrency)

    async def search(self, query: str) -> list[Game]:
        normalized_query = query.strip()
        if not normalized_query:
            return []
        escaped_query = normalized_query.replace("\\", "\\\\").replace('"', '\\"')
        body = (
            "fields id,name,first_release_date,platforms.name,genres.name,"
            "involved_companies.company.name,involved_companies.developer,"
            "involved_companies.publisher,cover.url,external_games.uid,"
            "external_games.external_game_source.name; "
            "where version_parent = null; "
            f'search "{escaped_query}"; limit {IGDB_PAGE_SIZE};'
        )
        payload = await self._post("games", body)
        return self._map_games(payload, "search")

    async def get_game(self, external_id: str) -> Game | None:
        normalized_id = external_id.strip()
        if not normalized_id.isdigit() or int(normalized_id) <= 0:
            return None
        body = (
            "fields id,name,summary,storyline,first_release_date,platforms.name,"
            "genres.name,game_modes.name,involved_companies.company.name,"
            "involved_companies.developer,involved_companies.publisher,cover.url,"
            "rating,rating_count,aggregated_rating,aggregated_rating_count,"
            "external_games.uid,external_games.external_game_source.name; "
            f"where id = {int(normalized_id)}; limit 1;"
        )
        payload = await self._post("games", body)
        if not payload:
            return None
        try:
            return map_igdb_game(payload[0])
        except (TypeError, ValueError):
            raise IgdbProviderError("IGDB returned invalid game details.") from None

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._token_manager.aclose()

    async def _post(self, endpoint: str, body: str) -> list[dict[str, Any]]:
        auth_retry = True
        for attempt in range(IGDB_MAX_RETRIES + 1):
            token = await self._token_manager.get_token()
            await self._limiter.acquire()
            try:
                try:
                    response = await self._client.post(
                        quote(endpoint, safe=""),
                        content=body,
                        headers={
                            "Client-ID": self._token_manager.client_id,
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "text/plain",
                        },
                    )
                except httpx.RequestError:
                    if attempt < IGDB_MAX_RETRIES:
                        await asyncio.sleep(0.25 * (2**attempt))
                        continue
                    raise IgdbProviderError(
                        "Could not complete the IGDB API request."
                    ) from None
            finally:
                self._limiter.release()

            if response.status_code == 401 and auth_retry:
                self._token_manager.invalidate()
                auth_retry = False
                continue
            if (
                response.status_code == 429 or response.status_code >= 500
            ) and attempt < IGDB_MAX_RETRIES:
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            if not 200 <= response.status_code < 300:
                raise IgdbProviderError(f"IGDB returned HTTP {response.status_code}.")
            try:
                payload = response.json()
            except ValueError:
                raise IgdbProviderError("IGDB returned invalid JSON.") from None
            if not isinstance(payload, list):
                raise IgdbProviderError("IGDB returned an invalid response body.")
            return [item for item in payload if isinstance(item, dict)]
        raise IgdbProviderError("IGDB request failed after retries.")

    @staticmethod
    def _map_games(payload: list[dict[str, Any]], operation: str) -> list[Game]:
        games: list[Game] = []
        for item in payload:
            try:
                games.append(map_igdb_game(item))
            except ValueError:
                # A single malformed community record must not break the full search.
                continue
        if not games and payload:
            raise IgdbProviderError(f"IGDB returned invalid game {operation} data.")
        return games
