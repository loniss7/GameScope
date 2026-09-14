from datetime import date

from app.matching import best_game_match, game_match_score, normalize_title
from app.schemas import Game


def test_title_normalization_removes_trademark_and_punctuation() -> None:
    assert normalize_title("The Witcher® 3: Wild Hunt") == "the witcher 3 wild hunt"


def test_game_match_uses_title_and_release_metadata() -> None:
    source = Game(title="The Witcher 3: Wild Hunt", release_date=date(2015, 5, 19))
    candidate = Game(title="The Witcher® 3 Wild Hunt", release_date=date(2015, 5, 19))

    assert game_match_score(source, candidate) == 1.0
    assert best_game_match(source, [candidate]) is not None


def test_match_rejects_weak_and_ambiguous_candidates() -> None:
    source = Game(title="Elden Ring")
    assert best_game_match(source, [Game(title="Cooking Simulator")]) is None

    first = Game(title="Elden Ring", external_ids={"steam": "1"})
    second = Game(title="Elden Ring", external_ids={"steam": "2"})
    assert best_game_match(source, [first, second]) is None


def test_match_rejects_same_title_with_conflicting_release_years() -> None:
    source = Game(title="Example Game", release_date=date(2020, 1, 1))
    unrelated_reissue = Game(title="Example Game", release_date=date(2024, 1, 1))

    assert best_game_match(source, [unrelated_reissue]) is None
