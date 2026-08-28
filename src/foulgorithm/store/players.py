"""Player-match history.

One row per player per match. This is the spine of every player market.

Two sources, both plain downloads:
  - worldfootballR_data, Aug 2017 to Sep 2025, 81k rows, FBref-derived
  - FPL-Core-Insights, 2024/25 onward, live, FotMob/Opta-derived

They overlap in 2024/25, which is useful: the overlap is how we check they
agree before trusting either.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path

import pandas as pd

from foulgorithm.sources.base import SourceError

WFR_URL = (
    "https://github.com/JaseZiv/worldfootballR_data/releases/download/"
    "fb_advanced_match_stats/ENG_M_1st_misc_player_advanced_match_stats.csv"
)
WFR_CACHE = Path("data/raw/worldfootballr/eng_misc_player_match.csv")

# Full-time stats publish shortly after the whistle. Three hours is conservative.
STATS_DELAY = timedelta(hours=3)

COLUMNS = [
    "player",
    "team",
    "opponent",
    "venue",
    "kickoff_utc",
    "known_at",
    "season",
    "position",
    "minutes",
    "fouls_committed",
    "fouls_drawn",
    "yellows",
    "reds",
    "tackles_won",
    "interceptions",
    "source",
]


def fetch_worldfootballr(cache: Path = WFR_CACHE) -> Path:
    """Download once, then read from disk forever. The repo is archived and frozen."""
    if cache.exists():
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(WFR_URL, headers={"User-Agent": "foulgorithm/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 200:
                raise SourceError(f"{WFR_URL} returned HTTP {response.status}")
            cache.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{WFR_URL} returned HTTP {exc.code}") from exc
    return cache


def load_all_leagues(codes: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Every league we hold a file for, in one frame, each row carrying its league.

    **Additive on purpose.** `load_player_matches()` is what every model reads
    and it still returns England alone, unchanged. Pooling is a modelling
    decision that belongs to roadmap item 8, not to a loader.

    The league column is not decoration. Serie A runs 1.197 fouls per 90 against
    England's 0.972, a 23% gap, while England's own eight-season spread is about
    9%. A pooled frame without it would overstate every Italian player by a
    fifth, silently. Anything fitting on this frame has to model the league.

    A league whose file is not on disk is simply absent. No empty rows, no
    placeholder: a league we do not hold and a league with no fouls have to look
    different.
    """
    from foulgorithm.sources import leagues as league_source

    wanted = codes or tuple(league_source.LEAGUES)
    frames = []
    for code in wanted:
        path = league_source.path_for(code)
        if not path.exists():
            continue
        frame = load_player_matches(path)
        frame["league"] = code
        frames.append(frame)

    if not frames:
        raise SourceError("no league files on disk. Run `make leagues` to download them.")
    return pd.concat(frames, ignore_index=True)


def load_player_matches(cache: Path = WFR_CACHE) -> pd.DataFrame:
    path = fetch_worldfootballr(cache)
    raw = pd.read_csv(path, low_memory=False)

    required = ["Player", "Team", "Match_Date", "Min", "Fls", "Fld", "Home_Away"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise SourceError(f"{path} is missing columns: {', '.join(missing)}")

    kickoff = pd.to_datetime(raw["Match_Date"], errors="coerce", utc=True)
    if kickoff.isna().any():
        raise SourceError(f"{path}: {int(kickoff.isna().sum())} rows have an unparseable date")

    # The file gives the fixture's teams, not the opponent directly.
    home_away = raw["Home_Away"].astype(str).str.strip().str.lower()
    opponent = pd.Series(
        [
            away if ha.startswith("home") else home
            for ha, home, away in zip(home_away, raw["Home_Team"], raw["Away_Team"], strict=True)
        ]
    )

    df = pd.DataFrame(
        {
            "player": raw["Player"].astype(str).str.strip(),
            "team": raw["Team"].astype(str).str.strip(),
            "opponent": opponent.astype(str).str.strip(),
            "venue": home_away.map(lambda x: "home" if x.startswith("home") else "away"),
            # No kickoff time in this file, so treat it as a late kickoff and let
            # known_at err later rather than earlier. Erring earlier would leak.
            "kickoff_utc": kickoff + timedelta(hours=20),
            "season": raw.get("Season_End_Year"),
            "position": raw.get("Pos"),
            "minutes": pd.to_numeric(raw["Min"], errors="coerce"),
            "fouls_committed": pd.to_numeric(raw["Fls"], errors="coerce"),
            "fouls_drawn": pd.to_numeric(raw["Fld"], errors="coerce"),
            "yellows": pd.to_numeric(raw.get("CrdY"), errors="coerce"),
            "reds": pd.to_numeric(raw.get("CrdR"), errors="coerce"),
            "tackles_won": pd.to_numeric(raw.get("TklW"), errors="coerce"),
            "interceptions": pd.to_numeric(raw.get("Int"), errors="coerce"),
            "source": "worldfootballr",
        }
    )
    df["known_at"] = df["kickoff_utc"] + STATS_DELAY

    # A handful of rows carry no minutes at all. Drop them and say how many,
    # rather than raising on a rounding error in someone else's export.
    core = ["minutes", "fouls_committed", "fouls_drawn"]
    blanks = int(df[core].isna().any(axis=1).sum())
    if blanks:
        if blanks > len(df) * 0.01:
            raise SourceError(f"{path}: {blanks} rows missing core stats, too many to drop")
        df = df.dropna(subset=core)

    # A player who did not get on the pitch tells us nothing about fouling.
    df = df[df["minutes"] > 0].copy()
    return df.sort_values("kickoff_utc").reset_index(drop=True)[COLUMNS]


def summarise(df: pd.DataFrame) -> str:
    per90 = df["fouls_committed"].sum() / (df["minutes"].sum() / 90)
    drawn90 = df["fouls_drawn"].sum() / (df["minutes"].sum() / 90)
    return (
        f"{len(df):,} player-matches | {df['player'].nunique():,} players | "
        f"{df['team'].nunique()} teams | "
        f"{df['kickoff_utc'].min():%b %Y} to {df['kickoff_utc'].max():%b %Y}\n"
        f"league rate: {per90:.2f} fouls committed per 90, {drawn90:.2f} drawn per 90"
    )
