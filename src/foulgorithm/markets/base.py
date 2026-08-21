"""Market definitions.

A market is a thing we predict. Adding one should mean adding a MarketSpec here,
not editing model or backtest code. See docs/05-markets.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EntityType = Literal["player", "team", "match"]

# Determines which distribution a model must return. Cards are binary, not a count:
# second yellows and straight reds are rare enough that "is this player booked at all"
# is the useful question, and a count model would waste capacity on a tail that
# almost never occurs.
DistributionFamily = Literal["count", "binary"]


@dataclass(frozen=True)
class MarketSpec:
    key: str
    label: str
    entity: EntityType
    family: DistributionFamily
    stat_column: str
    lines: tuple[float, ...]
    settlement_note: str
    min_minutes: int = 0

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError(f"{self.key}: needs at least one line")
        # Half-lines only. A whole-number line can push, which we have no way to price.
        for line in self.lines:
            if line * 2 % 2 == 0:
                raise ValueError(f"{self.key}: line {line} is a whole number, use half-lines")
        if self.family == "binary" and self.lines != (0.5,):
            raise ValueError(f"{self.key}: binary markets take exactly one line, 0.5")


_REGISTRY: dict[str, MarketSpec] = {}


def register(spec: MarketSpec) -> MarketSpec:
    if spec.key in _REGISTRY:
        raise ValueError(f"market {spec.key} is already registered")
    _REGISTRY[spec.key] = spec
    return spec


def get(key: str) -> MarketSpec:
    if key not in _REGISTRY:
        raise KeyError(f"unknown market {key!r}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def all_markets() -> dict[str, MarketSpec]:
    return dict(_REGISTRY)


PLAYER_FOULS_COMMITTED = register(
    MarketSpec(
        key="player_fouls_committed",
        label="Player fouls committed",
        entity="player",
        family="count",
        stat_column="fouls_committed",
        lines=(0.5, 1.5, 2.5, 3.5),
        settlement_note=(
            "Settles on the official data provider's fouls committed figure. Provider "
            "treatment of handballs, offsides and advantage situations differs and is "
            "NOT yet verified. See docs/12-risks-and-open-questions.md before making "
            "any claim of value against a bookmaker price."
        ),
        min_minutes=15,
    )
)

PLAYER_TACKLES = register(
    MarketSpec(
        key="player_tackles",
        label="Player tackles",
        entity="player",
        family="count",
        stat_column="tackles",
        lines=(0.5, 1.5, 2.5, 3.5),
        settlement_note=(
            "Providers differ on whether a tackle requires winning the ball, which "
            "materially changes the number. Verify against the settling provider."
        ),
        min_minutes=15,
    )
)

MATCH_TOTAL_FOULS = register(
    MarketSpec(
        key="match_total_fouls",
        label="Match total fouls",
        entity="match",
        family="count",
        stat_column="total_fouls",
        lines=(20.5, 22.5, 24.5, 26.5),
        settlement_note=(
            "Both teams' fouls committed, combined. Priced more efficiently than "
            "player markets, so the edge here is smaller. Built first because it "
            "needs no player-level data and validates the whole pipeline."
        ),
    )
)

PLAYER_CARDS = register(
    MarketSpec(
        key="player_cards",
        label="Player to be booked",
        entity="player",
        family="binary",
        stat_column="was_carded",
        lines=(0.5,),
        settlement_note=(
            "Yellow or red at any point, including after being substituted. Excludes "
            "cards shown to non-playing staff and retrospective post-match cards."
        ),
        min_minutes=1,
    )
)
