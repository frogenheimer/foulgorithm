"""The house model, and how the five are scored against each other.

**The house model is the five averaged.** Each of them is wrong in its own
direction and the errors are not perfectly correlated, so half of each cancels.
It is a sixth opinion rather than a judge of the other five, and it has no
temperament, no weakness worth naming and nothing to explore. That is what makes
it the right thing to put on a fixture card.

**The league table is the five scored on identical bets.** Comparing characters
is only fair when they are asked the same question, so every gameweek each one
must produce the same fixed slates: six players at 1+, three at 2+, and a mixed
two-and-two. A character that would rather pass has to commit.

Scoring reads as a football table, which is the right metaphor for a site about
football:

  - every leg lands, three points
  - all but one lands, one point
  - anything worse, none
  - goal difference is legs landed minus legs missed

Weights are equal until there is a record to fit them on. The parameter exists
so that day does not need a rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass


def blend(probabilities: list[float], weights: list[float] | None = None) -> float:
    """The house number: a weighted mean of the five.

    Refuses an empty list rather than returning a default, because a default
    here is a made-up number on the front page.
    """
    if not probabilities:
        raise ValueError("nothing to blend")
    if weights is None:
        return sum(probabilities) / len(probabilities)
    if len(weights) != len(probabilities):
        raise ValueError(f"{len(weights)} weights for {len(probabilities)} probabilities")
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to something positive")
    return sum(p * w for p, w in zip(probabilities, weights, strict=False)) / total


@dataclass(frozen=True)
class Slate:
    """A fixed bet shape every character must produce every gameweek."""

    key: str
    label: str
    # (line, how many legs at it). A line of 0.5 means "1+ fouls".
    shape: tuple[tuple[float, int], ...]

    @property
    def legs(self) -> int:
        return sum(n for _, n in self.shape)


# Identical shapes, so a hit count is directly comparable. Difficulty is held
# constant and only the selection varies, which is the thing being measured.
SLATES: tuple[Slate, ...] = (
    Slate("six-ones", "Six at 1+", ((0.5, 6),)),
    Slate("three-twos", "Three at 2+", ((1.5, 3),)),
    Slate("two-and-two", "Two at 2+, two at 1+", ((1.5, 2), (0.5, 2))),
)


@dataclass(frozen=True)
class Tier:
    """A fixed count of FOUL EVENTS every slip must need (docs/45).

    A leg's events are its line: 1+ is one, 2+ two, 3+ three; a slip's legs
    sum to the count exactly. Layout is free inside it. 3+ legs are reserved
    for the rogue slip, and only for a player the house prices at
    ROGUE_3PLUS_FLOOR or better there, because 3+ is wild.
    """

    key: str
    label: str
    units: int
    allows_three: bool


TIERS: tuple[Tier, ...] = (
    Tier("safe", "Safe", 4, False),
    Tier("optimistic", "Optimistic", 5, False),
    Tier("rogue", "Rogue", 6, True),
)

#: The house's 3+ price a player needs before a rogue slip may carry him at 3+.
ROGUE_3PLUS_FLOOR = 0.20

#: Games kicking off from here are bet by foul events (docs/45). Earlier games
#: keep the shapes and are scored under them: matchweek 2 was committed under
#: the old contract and the record does not rewrite history.
PRICED_FROM = "2026-09-04"


def priced(kickoff_iso: str) -> bool:
    return str(kickoff_iso)[:10] >= PRICED_FROM


def score_priced(pairs: list[tuple[bool, int]]) -> dict:
    """Points for one priced bet, from (landed, deficit) per leg.

    Bets no longer share a leg count, so the near miss is measured in fouls:
    every leg landing is a win, the bet falling exactly ONE foul short in
    total is a draw, anything else is a loss. Same points as the shapes.
    """
    if not pairs:
        return {"points": 0, "result": "void", "landed": 0, "missed": 0, "difference": 0}
    landed = sum(1 for ok, _ in pairs if ok)
    missed = len(pairs) - landed
    short = sum(deficit for ok, deficit in pairs if not ok)
    if missed == 0:
        points, result = 3, "won"
    elif short == 1:
        points, result = 1, "drawn"
    else:
        points, result = 0, "lost"
    return {
        "points": points,
        "result": result,
        "landed": landed,
        "missed": missed,
        "difference": landed - short,
    }


def score_slate(legs: list[bool]) -> dict:
    """Points and difference for one slate, read as a football result.

    A near miss is not a wipeout. Scoring "all but one" the same as "none of
    them" throws away most of what separates a good week from a bad one.
    """
    if not legs:
        return {"points": 0, "result": "void", "landed": 0, "missed": 0, "difference": 0}

    landed = sum(1 for x in legs if x)
    missed = len(legs) - landed

    if missed == 0:
        points, result = 3, "won"
    elif missed == 1:
        points, result = 1, "drawn"
    else:
        points, result = 0, "lost"

    return {
        "points": points,
        "result": result,
        "landed": landed,
        "missed": missed,
        "difference": landed - missed,
    }
