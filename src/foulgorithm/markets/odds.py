"""Odds arithmetic, kept in one place because getting it wrong is quiet.

The tiers were held as decimal prices and rendered as fractional ones, so a
decimal 2.0, which is evens, appeared on the site as "2/1". Every published tier
was one step longer than it read, and nothing failed.

The margin functions exist because a bookmaker's take compounds per leg. It is
the whole reason accumulators get pushed: at 15% a leg, a three-leg combination
has 34% taken out of it rather than 15%.
"""

from __future__ import annotations

from fractions import Fraction

# Measured from 4,180 Premier League matches in our own files: Pinnacle 2.6%,
# Bet365 4.3%, Betway 5.1%, William Hill 5.3%. Those are MATCH odds, the most
# liquid market on the board. Margin scales inversely with liquidity and player
# props are far thinner, so 15% is the working assumption for a foul market and
# it is stated on the page rather than buried here.
PROP_MARGIN = 0.15

# What a bet must pay above fair to be worth taking. Backing at exactly fair
# odds returns nothing in expectation, so the margin is the entire point.
EDGE = 0.10


def to_decimal(probability: float) -> float:
    if not 0 < probability <= 1:
        raise ValueError(f"probability {probability} is not in (0, 1]")
    return 1.0 / probability


def to_probability(decimal: float) -> float:
    if decimal <= 0:
        raise ValueError(f"decimal price {decimal} is not positive")
    return 1.0 / decimal


def fractional(decimal: float, max_denominator: int = 20) -> str:
    """Decimal to the fractional form punters actually read.

    Decimal 3.0 is 2/1, not 3/1. Odds-on prices keep a readable fraction rather
    than collapsing to "0/1": 1.5 is 1/2.
    """
    if decimal <= 1:
        raise ValueError(f"decimal price {decimal} implies certainty or better")
    f = Fraction(decimal - 1).limit_denominator(max_denominator)
    return f"{f.numerator}/{f.denominator}"


def take_out(legs: int = 1, margin: float = PROP_MARGIN) -> float:
    """The share of a combination's value the margin removes.

    Compounds. One leg at 15% loses 13%; three legs lose 34%; five lose 50%.
    """
    if margin < 0:
        raise ValueError("a negative margin means a bookmaker offering better than fair")
    if legs < 1:
        raise ValueError("a combination needs at least one leg")
    return 1.0 - 1.0 / (1.0 + margin) ** legs


def offered(fair: float, legs: int = 1, margin: float = PROP_MARGIN) -> float:
    """What a bookmaker would likely offer against a fair price.

    An estimate, and never an observation: no player-fouls price has ever been
    published anywhere we can reach, which is why this is a stated assumption
    with the margin shown next to it.
    """
    if margin < 0:
        raise ValueError("a negative margin means a bookmaker offering better than fair")
    return fair / (1.0 + margin) ** legs


def floor(fair: float, edge: float = EDGE) -> float:
    """The lowest price worth taking. Fair returns nothing in expectation."""
    return fair * (1.0 + edge)


def verdict(fair: float, offered: float, edge: float = EDGE) -> str:
    """Three words, stated rather than left as two numbers to compare.

    ⚠️ Only meaningful against an OBSERVED price. Comparing against
    `offered()`, which is derived from `fair` by removing a margin, is
    circular: the answer is always "below fair" because the margin put it
    there. Use `take_out()` to describe an estimate, and keep this for the day
    a real price exists to check against.
    """
    if offered < fair:
        return "below fair"
    if offered < floor(fair, edge):
        return "fair, under our margin"
    return "worth taking"
