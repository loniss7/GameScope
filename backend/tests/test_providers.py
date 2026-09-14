import asyncio

import pytest

from app.providers import GameProvider
from app.schemas import Game


class ExampleGameProvider(GameProvider):
    async def search(self, query: str) -> list[Game]:
        return [Game(title=query, external_ids={"example": "game-1"})]

    async def get_game(self, external_id: str) -> Game | None:
        if external_id != "game-1":
            return None
        return Game(title="Example Game", external_ids={"example": external_id})


def test_provider_requires_both_contract_methods() -> None:
    class IncompleteProvider(GameProvider):
        pass

    with pytest.raises(TypeError, match="abstract"):
        IncompleteProvider()


def test_concrete_provider_returns_normalized_games() -> None:
    provider = ExampleGameProvider()

    search_results = asyncio.run(provider.search("Example Game"))
    details = asyncio.run(provider.get_game("game-1"))
    missing_game = asyncio.run(provider.get_game("missing"))

    assert search_results == [
        Game(title="Example Game", external_ids={"example": "game-1"})
    ]
    assert details == Game(title="Example Game", external_ids={"example": "game-1"})
    assert missing_game is None
