from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import Game, GameRating


def test_game_accepts_normalized_data_and_separate_external_ids() -> None:
    game = Game(
        id="gamescope-1",
        title="  Example Game  ",
        release_date="2024-05-20",
        developers=["Example Studio"],
        genres=["Adventure"],
        platforms=["PC"],
        ratings=[
            {
                "source": "rawg",
                "score": 4.5,
                "max_score": 5,
                "rating_count": 120,
            }
        ],
        external_ids={"rawg": "12345", "steam": "67890"},
    )

    assert game.title == "Example Game"
    assert game.release_date == date(2024, 5, 20)
    assert game.ratings[0].score == 4.5
    assert game.id == "gamescope-1"
    assert game.external_ids == {"rawg": "12345", "steam": "67890"}


def test_game_collection_defaults_are_independent() -> None:
    first = Game(title="First game")
    second = Game(title="Second game")

    first.platforms.append("PC")

    assert second.platforms == []


def test_game_requires_non_blank_title() -> None:
    with pytest.raises(ValidationError):
        Game(title="   ")


@pytest.mark.parametrize(
    "rating_data",
    [
        {"source": "rawg", "score": 6, "max_score": 5},
        {"source": "rawg", "score": 1, "max_score": 0},
        {"source": "rawg", "score": 1, "max_score": 5, "rating_count": -1},
    ],
)
def test_game_rating_rejects_invalid_values(rating_data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        GameRating.model_validate(rating_data)
