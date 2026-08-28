"""Twenty seasons of official league totals, as one tidy table.

One row per player per season, every stat a column, rates derived here rather
than in each caller. A per-90 computed three ways in three places is three
chances to divide by the wrong denominator.

**Validation is the point of this module, not the reading.** The source that fed
this project sat frozen for eleven months and nothing failed anywhere, so a
shape change has to surface here, at the boundary, rather than as a KeyError
deep inside a model where it looks like a modelling bug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

STORE = Path("data/raw/pulselive/player_seasons")

#: Every file must carry these, or we cannot tell fresh data from stale.
REQUIRED = ("season", "players", "rows", "fetchedAt")

#: Counts worth having as rates. Anything else stays a raw count.
RATED = (
    "fouls",
    "was_fouled",
    "fouled_final_third",
    "total_tackle",
    "won_tackle",
    "attempted_tackle_foul",
    "challenge_lost",
    "duel_won",
    "duel_lost",
    "aerial_won",
    "aerial_lost",
    "total_contest",
    "won_contest",
    "dispossessed",
    "yellow_card",
    "interception",
    "total_clearance",
    "ball_recovery",
    "touches",
)

EMPTY = ["player", "season", "seasonId", "mins_played", "appearances"]


def _check(path: Path, held: dict) -> None:
    missing = [k for k in REQUIRED if not held.get(k) and held.get(k) != 0]
    if missing:
        raise ValueError(f"{path.name} is missing {', '.join(missing)}")

    rows = held.get("rows")
    players = held.get("players") or []
    if rows != len(players):
        raise ValueError(
            f"{path.name} says rows={rows} but carries {len(players)}. "
            "A truncated write is silent otherwise."
        )


def load(root: Path = STORE) -> pd.DataFrame:
    """Every season on disk, validated, with rates derived."""
    if not root.exists():
        return pd.DataFrame(columns=EMPTY)

    frames = []
    for path in sorted(root.glob("*.json")):
        try:
            held = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} is not readable JSON: {exc}") from exc

        _check(path, held)
        if held["players"]:
            frame = pd.DataFrame(held["players"])
            # When this reading was taken, per row, because an in-progress
            # season's totals were knowable only at that moment. The latest
            # touch wins: a repaired or backfilled file's values are that
            # pass's reading, not the original fetch's.
            frame["fetchedAt"] = max(
                stamp
                for stamp in (
                    held.get("fetchedAt"),
                    held.get("backfilledAt"),
                    held.get("repairedAt"),
                )
                if stamp
            )
            frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=EMPTY)

    out = pd.concat(frames, ignore_index=True)

    # Rates, once, here.
    #
    # No minutes means no rate rather than infinity, and an unrecorded count
    # stays unrecorded: a player the league did not rank for fouls has not been
    # shown to foul nobody.
    if "mins_played" in out.columns:
        nineties = pd.to_numeric(out["mins_played"], errors="coerce") / 90.0
        nineties = nineties.where(nineties > 0)
        for stat in RATED:
            if stat in out.columns:
                out[f"{stat}_per_90"] = pd.to_numeric(out[stat], errors="coerce") / nineties

    return out


def coverage(root: Path = STORE) -> pd.DataFrame:
    """What we actually hold, per season. For reporting, not for modelling."""
    frame = load(root)
    if frame.empty:
        return frame

    return (
        frame.assign(has_fouls=frame["fouls"].notna() if "fouls" in frame else False)
        .groupby("season")
        .agg(
            players=("player", "nunique"),
            with_fouls=("has_fouls", "sum"),
            minutes=("mins_played", "sum"),
        )
        .reset_index()
        .sort_values("season")
    )
