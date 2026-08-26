"""What a division's average club looks like, so a raw number has a scale.

Championship referees whistle differently from Premier League ones, and the
spread of club rates is far wider in the second tier. `features/promotion.py`
measured the consequence: only about 37% of a promoted club's deviation from
its Championship average carries into the Premier League, and taking the raw
rate at face value scores 16% WORSE than using the league mean.

So a cup page showing "Burnley 13.1, Arsenal 10.4" side by side reads as a fact
about Burnley when part of it is a fact about the division. The fix is not to
adjust either number, which would be a model judgement in a section that has
none, but to publish each next to its OWN division's mean. The reader sees two
scales and can see they are two scales.
"""

from __future__ import annotations

from foulgorithm.identity.teams import CHAMPIONSHIP, PREMIER

DIVISION_NAMES = {PREMIER: "Premier League", CHAMPIONSHIP: "Championship"}

#: Every stat a TeamRecord carries that a baseline is meaningful for, mapped to
#: the pair of row columns it averages. Home and away are pooled: a division's
#: average club plays half its matches at each.
_STATS = {
    "foulsPerMatch": ("home_fouls", "away_fouls"),
    "foulsWonPerMatch": ("away_fouls", "home_fouls"),
    "yellowsPerMatch": ("home_yellows", "away_yellows"),
    "redsPerMatch": ("home_reds", "away_reds"),
    "shotsPerMatch": ("home_shots", "away_shots"),
    "shotsOnTargetPerMatch": ("home_shots_on_target", "away_shots_on_target"),
    "cornersPerMatch": ("home_corners", "away_corners"),
    "goalsForPerMatch": ("home_goals", "away_goals"),
    "goalsAgainstPerMatch": ("away_goals", "home_goals"),
}


def build(matches: list[dict]) -> dict[str, float]:
    """Mean per team-innings across a division. Empty in, empty out."""
    if not matches:
        return {}

    out: dict[str, float] = {"matches": len(matches)}
    for name, (home_col, away_col) in _STATS.items():
        values = [
            v
            for m in matches
            for v in (m.get(home_col), m.get(away_col))
            if v is not None
        ]
        if values:
            out[name] = round(sum(values) / len(values), 2)

    # Cards per foul, the column worth reading. Same reasoning as
    # publish/site_export: cards per match rises with how physical a game was.
    carded = [
        m for m in matches
        if m.get("home_yellows") is not None and m.get("away_yellows") is not None
    ]
    fouls = sum((m["home_fouls"] or 0) + (m["away_fouls"] or 0) for m in carded)
    cards = sum(
        (m["home_yellows"] or 0) + (m["away_yellows"] or 0)
        + (m.get("home_reds") or 0) + (m.get("away_reds") or 0)
        for m in carded
    )
    if fouls:
        out["cardsPerFoul"] = round(cards / fouls, 4)

    return out


def delta(value: float | None, baseline: dict, stat: str) -> float | None:
    """How far above or below its division a club sits. None if either is absent."""
    if value is None:
        return None
    mean = baseline.get(stat)
    if mean is None:
        return None
    return round(value - mean, 2)


def marker(value: float | None, baseline: dict, stat: str, division: str) -> str | None:
    """The line printed under a raw number: "+1.4 v Championship".

    The division is named on purpose. A bare "+1.4" beside another club's bare
    "+0.3" invites the reader to compare the two deltas, which is the same
    cross-league mistake in a different costume.
    """
    d = delta(value, baseline, stat)
    if d is None:
        return None
    name = DIVISION_NAMES.get(division, division)
    if d == 0:
        return f"level with {name}"
    return f"{d:+.1f} v {name}"


def rank(value: float | None, rates: dict[str, float]) -> tuple[int, int] | None:
    """Where this rate sits in its division, highest first. `(place, of)`.

    Rank earns its place because the two divisions barely differ in LEVEL and
    differ a lot in SPREAD. Over the published window the Premier League
    averages 10.75 fouls a match and the Championship 10.81, while the
    Championship spread is 40% wider. So "+1.4" is a bigger claim in one league
    than the other and a reader cannot see which. "3rd of 24" carries the same
    meaning in both.

    A value not already in `rates` is ranked against them anyway, which is what
    happens when a club is compared with the division it just left.
    """
    if value is None or not rates:
        return None
    values = list(rates.values())
    if value not in values:
        values.append(value)
    higher = sum(1 for v in values if v > value)
    return higher + 1, len(values)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }".replace(" ", "")


def rank_label(place: tuple[int, int] | None, division: str) -> str | None:
    """"3rd most in the Championship of 24". Top and bottom get plain words."""
    if place is None:
        return None
    n, of = place
    name = DIVISION_NAMES.get(division, division)
    if n == 1:
        return f"most in the {name} of {of}"
    if n == of:
        return f"fewest in the {name} of {of}"
    return f"{_ordinal(n)} most in the {name} of {of}"
