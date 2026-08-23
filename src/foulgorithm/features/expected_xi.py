"""Predicting the eleven, before the confirmed one lands at T-60.

Every player bet depends on the player playing, so this is the highest-leverage
guess in the system and it was the crudest thing in it.

Measured over 1,058 team-matches:

| method | slots correct |
|---|---|
| rank on this season's starts | 63.1% |
| whoever started the last match | **76.5%** |
| last eleven, topped up from the ranking | **78.1%** |

A fifteen-point gain for a simpler rule. Sportmonks sells a curated feed at
about 84% for 34 euros a month, so this closes roughly two thirds of that gap
for nothing.

Availability is applied on top. FPL carries club-sourced injury and suspension
status, so a player ruled out cannot survive into a prediction merely because he
started last week.
"""

from __future__ import annotations

import pandas as pd

# Below this a player came off the bench. A cameo is not a start, and a bet
# settles on someone playing the match.
STARTER_MINUTES = 60


def last_eleven(history: pd.DataFrame, team: str, as_of) -> set[str]:
    """Who started this club's most recent match before `as_of`.

    Filtered by `known_at` rather than kickoff, so a match played but not yet
    reported cannot inform a prediction. Same rule as everywhere else here.
    """
    # An empty frame has no columns to filter on.
    if history.empty:
        return set()
    rows = history[
        (history["team"] == team)
        & (history["known_at"] <= as_of)
        & (history["minutes"] >= STARTER_MINUTES)
    ]
    if rows.empty:
        return set()
    latest = rows["kickoff_utc"].max()
    return set(rows[rows["kickoff_utc"] == latest]["player"].head(11))


def assemble(last: list[str], fallback: list[str], unavailable: set[str], size: int = 11) -> list[str]:
    """The last eleven, minus anyone ruled out, topped up from the fallback.

    Order matters: the last eleven leads because it is the better predictor, and
    the fallback only fills gaps. Topping up is what takes 76.5% to 78.1%, since
    a club that rotated heavily or had a player sent off leaves the last eleven
    short.
    """
    picked: list[str] = []
    seen: set[str] = set()
    for name in [*last, *fallback]:
        if len(picked) >= size:
            break
        if name in seen or name in unavailable:
            continue
        picked.append(name)
        seen.add(name)
    return picked
