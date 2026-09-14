import asyncio

from app.aggregators import GameAggregator, merge_games
from app.providers import GameProvider, GameProviderError
from app.schemas import Game, GameRating


class FakeProvider(GameProvider):
    name = "fake"

    def __init__(
        self, games: list[Game], details: Game | None = None, error: bool = False
    ) -> None:
        self.games = games
        self.details = details
        self.error = error

    async def search(self, query: str) -> list[Game]:
        if self.error:
            raise GameProviderError("provider unavailable")
        return self.games

    async def get_game(self, external_id: str) -> Game | None:
        return self.details


def test_merge_prefers_primary_and_unions_provider_data() -> None:
    merged = merge_games(
        Game(
            title="Example",
            genres=["RPG"],
            ratings=[GameRating(source="rawg", score=4, max_score=5)],
            external_ids={"rawg": "1"},
        ),
        Game(
            title="Example (Steam)",
            description="Steam description",
            genres=["rpg", "Action"],
            ratings=[GameRating(source="steam", score=80, max_score=100)],
            external_ids={"steam": "2"},
        ),
    )

    assert merged.title == "Example"
    assert merged.description == "Steam description"
    assert merged.genres == ["RPG", "Action"]
    assert {rating.source for rating in merged.ratings} == {"rawg", "steam"}
    assert merged.external_ids == {"rawg": "1", "steam": "2"}


def test_aggregator_enriches_with_matching_provider_and_tolerates_failure() -> None:
    rawg = FakeProvider(
        [],
        Game(title="The Witcher 3: Wild Hunt", external_ids={"rawg": "1"}),
    )
    steam = FakeProvider(
        [Game(title="The Witcher\u00ae 3: Wild Hunt", external_ids={"steam": "2"})],
        Game(
            title="The Witcher 3",
            description="Steam details",
            external_ids={"steam": "2"},
        ),
    )
    steam.name = "steam"
    failed = FakeProvider([], error=True)

    result = asyncio.run(GameAggregator(rawg, [steam, failed]).get_game("1"))

    assert result is not None
    assert result.description == "Steam details"
    assert result.external_ids == {"rawg": "1", "steam": "2"}
