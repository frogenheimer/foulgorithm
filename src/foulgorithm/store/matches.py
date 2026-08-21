"""Load match history into a single frame.

Everything downstream reads this. Rows are sorted by kickoff and carry
`known_at`, which is what the harness filters on to prevent leakage.
"""

from __future__ import annotations

import pandas as pd

from foulgorithm.publish.site_export import season_labels
from foulgorithm.sources import football_data

COLUMNS = [
    "season",
    "kickoff_utc",
    "known_at",
    "home_team_raw",
    "away_team_raw",
    "referee_raw",
    "home_fouls",
    "away_fouls",
    "home_yellows",
    "away_yellows",
    "home_reds",
    "away_reds",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_corners",
    "away_corners",
    "odds_home",
    "odds_draw",
    "odds_away",
]


def load_matches(seasons: list[str] | None = None, quiet: bool = True) -> pd.DataFrame:
    seasons = seasons or season_labels()
    frames = []
    for label in seasons:
        try:
            rows = football_data.parse(football_data.fetch(label))
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            if not quiet:
                print(f"  skipped {label}: {exc}")
            continue
        for row in rows:
            row["season"] = label
        frames.append(pd.DataFrame(rows))

    if not frames:
        raise RuntimeError("no seasons loaded")

    df = pd.concat(frames, ignore_index=True)
    df = _attach_odds(df, seasons)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df["total_fouls"] = df["home_fouls"] + df["away_fouls"]
    df = df.sort_values("kickoff_utc").reset_index(drop=True)
    return df


def _attach_odds(df: pd.DataFrame, seasons: list[str]) -> pd.DataFrame:
    """Closing 1X2 odds where the file carries them, which is 2019/20 onward.

    Read straight from the raw CSV because the adapter's typed output covers
    match statistics only. Missing odds stay missing rather than being filled.
    """
    import csv
    import io

    wanted = {"AvgCH": "odds_home", "AvgCD": "odds_draw", "AvgCA": "odds_away"}
    fallback = {"AvgH": "odds_home", "AvgD": "odds_draw", "AvgA": "odds_away"}

    lookup: dict[tuple, dict] = {}
    for label in seasons:
        try:
            raw = football_data.fetch(label)
        except Exception:  # noqa: BLE001
            continue
        reader = csv.DictReader(io.StringIO(raw.text()))
        cols = set(reader.fieldnames or [])
        mapping = wanted if wanted.keys() <= cols else (fallback if fallback.keys() <= cols else None)
        if mapping is None:
            continue
        for rec in reader:
            key = (label, (rec.get("HomeTeam") or "").strip(), (rec.get("AwayTeam") or "").strip())
            if not key[1]:
                continue
            lookup[key] = {
                target: _as_float(rec.get(source)) for source, target in mapping.items()
            }

    for target in ("odds_home", "odds_draw", "odds_away"):
        df[target] = [
            lookup.get((s, h, a), {}).get(target)
            for s, h, a in zip(df["season"], df["home_team_raw"], df["away_team_raw"], strict=True)
        ]
    return df


def _as_float(value: str | None) -> float | None:
    try:
        return float((value or "").strip())
    except ValueError:
        return None
