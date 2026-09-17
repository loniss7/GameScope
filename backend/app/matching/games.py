import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.schemas import Game

_TRADEMARKS = re.compile(r"[®™©]")
_NON_ALPHANUMERIC = re.compile(r"[^\w]+", re.UNICODE)


@dataclass(frozen=True)
class GameMatch:
    game: Game
    confidence: float


def normalize_title(title: str) -> str:
    """Normalize titles while preserving meaningful words and edition markers."""
    value = unicodedata.normalize("NFKC", title).casefold()
    value = _TRADEMARKS.sub("", value)
    value = _NON_ALPHANUMERIC.sub(" ", value)
    return " ".join(value.split())


def game_match_score(left: Game, right: Game) -> float:
    left_title = normalize_title(left.title)
    right_title = normalize_title(right.title)
    if not left_title or not right_title:
        return 0.0
    if left_title == right_title:
        score = 1.0
    else:
        left_tokens = set(left_title.split())
        right_tokens = set(right_title.split())
        token_score = len(left_tokens & right_tokens) / max(
            len(left_tokens | right_tokens), 1
        )
        sequence_score = SequenceMatcher(None, left_title, right_title).ratio()
        score = 0.7 * sequence_score + 0.3 * token_score

    if left.release_date and right.release_date:
        score += 0.04 if left.release_date.year == right.release_date.year else -0.25
    left_developers = {name.casefold() for name in left.developers}
    right_developers = {name.casefold() for name in right.developers}
    if left_developers and right_developers:
        score += 0.04 if left_developers & right_developers else -0.05
    left_platforms = {name.casefold() for name in left.platforms}
    right_platforms = {name.casefold() for name in right.platforms}
    if left_platforms and right_platforms:
        score += 0.02 if left_platforms & right_platforms else -0.04
    return round(max(0.0, min(score, 1.0)), 4)


def best_game_match(
    source: Game,
    candidates: list[Game],
    *,
    threshold: float = 0.78,
    ambiguity_margin: float = 0.025,
) -> GameMatch | None:
    """Return the highest-confidence candidate, refusing weak or ambiguous matches."""
    if not candidates:
        return None
    scored = sorted(
        (
            GameMatch(game=candidate, confidence=game_match_score(source, candidate))
            for candidate in candidates
        ),
        key=lambda match: match.confidence,
        reverse=True,
    )
    best = scored[0]
    if best.confidence < threshold:
        return None
    if len(scored) > 1 and best.confidence - scored[1].confidence < ambiguity_margin:
        return None
    return best
