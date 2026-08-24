"""Twenty seasons of team match stats, as one tidy table.

One row per team per match, every stat a column, roughly 180 of them. Compare
with the six we hold from football-data.co.uk.

Same validation as the season store, for the same reason: the source that fed
this project sat frozen for eleven months and nothing failed anywhere. A file
whose row count disagrees with its contents is a truncated write and is rejected
here, at the boundary.

**One caution.** This is the same provider as the season totals, which read
about 4.6% above the FBref archive on fouls. Anything mixing this with the
archive needs that term. See `docs/28-foul-data-sources.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

STORE = Path("data/raw/pulselive/team_matches")

REQUIRED = ("season", "teams", "rows", "fetchedAt")

EMPTY = ["fixtureId", "teamId", "home", "away", "kickoff", "season"]

#: The league's names for the two foul markets, at team level.
FOULS_COMMITTED = "fk_foul_lost"
FOULS_DRAWN = "fk_foul_won"


def _check(path: Path, held: dict) -> None:
    missing = [k for k in REQUIRED if not held.get(k) and held.get(k) != 0]
    if missing:
        raise ValueError(f"{path.name} is missing {', '.join(missing)}")

    rows = held.get("rows")
    teams = held.get("teams") or []
    if rows != len(teams):
        raise ValueError(
            f"{path.name} says rows={rows} but carries {len(teams)}. "
            "A truncated write is silent otherwise."
        )


def load(root: Path = STORE) -> pd.DataFrame:
    """Every season on disk, validated."""
    if not root.exists():
        return pd.DataFrame(columns=EMPTY)

    frames = []
    for path in sorted(root.glob("*.json")):
        try:
            held = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} is not readable JSON: {exc}") from exc

        _check(path, held)
        if held["teams"]:
            frame = pd.DataFrame(held["teams"])
            frame["season"] = held["season"]
            frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=EMPTY)
    return pd.concat(frames, ignore_index=True)


def match_totals(frame: pd.DataFrame) -> pd.DataFrame:
    """Both sides of each match summed, one row per fixture.

    A fixture with only one team recorded is dropped rather than halved. Half a
    match's fouls presented as a total reads as a quiet game, which is the same
    class of error as a missing player reading as a clean one.
    """
    if frame.empty or FOULS_COMMITTED not in frame.columns:
        return pd.DataFrame(columns=["fixtureId", "home", "away", "fouls"])

    counted = frame.groupby("fixtureId").size()
    complete = set(counted[counted == 2].index)
    both = frame[frame["fixtureId"].isin(complete)]
    if both.empty:
        return pd.DataFrame(columns=["fixtureId", "home", "away", "fouls"])

    return (
        both.groupby("fixtureId")
        .agg(
            home=("home", "first"),
            away=("away", "first"),
            kickoff=("kickoff", "first"),
            season=("season", "first"),
            fouls=(FOULS_COMMITTED, "sum"),
        )
        .reset_index()
    )


def coverage(root: Path = STORE) -> pd.DataFrame:
    """What we hold per season. For reporting, not modelling."""
    frame = load(root)
    if frame.empty:
        return frame
    return (
        frame.groupby("season")
        .agg(
            team_matches=("fixtureId", "size"),
            fixtures=("fixtureId", "nunique"),
            stats=("fixtureId", lambda _: len(frame.columns)),
        )
        .reset_index()
        .sort_values("season")
    )
