import asyncio
import sys
from pathlib import Path

# Support the documented `python scripts/search_game.py` invocation from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.providers.rawg import RawgProvider, RawgProviderError


async def _search(query: str) -> None:
    settings = get_settings()
    provider = RawgProvider(
        settings.rawg_api_key,
        timeout_seconds=settings.rawg_timeout_seconds,
    )
    try:
        games = await provider.search(query)
        print("[" + ",\n".join(game.model_dump_json(indent=2) for game in games) + "]")
    finally:
        await provider.aclose()


def main() -> int:
    try:
        query = input("Enter a game title: ").strip()
        if not query:
            print("A non-empty game title is required.", file=sys.stderr)
            return 2
        asyncio.run(_search(query))
    except (RawgProviderError, ValueError) as error:
        print(f"Search failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Search cancelled.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
