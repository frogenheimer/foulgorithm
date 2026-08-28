"""Inventory of everything we hold.

Answers, honestly: what data do we have, how much, how complete is it, and is it
enough to model on. Run with `make audit`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from foulgorithm.store.matches import load_matches

RAW = Path("data/raw")

# Rough guide for how much evidence a rate needs before it stops being a guess.
# Not a hard threshold, just a marker for the report.
RELIABLE_MATCHES = 30


def audit() -> None:
    df = load_matches()
    print("=" * 74)
    print("FOULGORITHM DATA INVENTORY")
    print("=" * 74)

    _files()
    _coverage(df)
    _completeness(df)
    _samples(df)
    _reliability(df)
    _missing()


def _files() -> None:
    print("\n## RAW CACHE (local files, never re-downloaded)\n")
    if not RAW.exists():
        print("  none")
        return
    total = 0
    for source in sorted(RAW.iterdir()):
        if not source.is_dir():
            continue
        files = list(source.rglob("*.csv"))
        size = sum(f.stat().st_size for f in files)
        total += size
        print(f"  {source.name:<20} {len(files):>4} files   {size / 1_048_576:>6.1f} MB")
    print(f"  {'TOTAL':<20} {'':>4}         {total / 1_048_576:>6.1f} MB")


def _coverage(df: pd.DataFrame) -> None:
    print("\n## COVERAGE\n")
    print(f"  Matches              {len(df):,}")
    print(
        f"  Seasons              {df['season'].nunique()} ({df['season'].min()} to {df['season'].max()})"
    )
    print(f"  Teams seen           {len(set(df['home_team_raw']) | set(df['away_team_raw']))}")
    print(f"  Referees seen        {df['referee_raw'].nunique()}")
    print(
        f"  Date range           {df['kickoff_utc'].min():%d %b %Y} to {df['kickoff_utc'].max():%d %b %Y}"
    )
    print(f"  Total fouls recorded {int(df['total_fouls'].sum()):,}")


def _completeness(df: pd.DataFrame) -> None:
    print("\n## COMPLETENESS (per column)\n")
    print(f"  {'column':<24}{'filled':>10}{'%':>8}   note")
    print("  " + "-" * 66)
    notes = {
        "odds_home": "closing odds only exist from 2019-20",
        "odds_draw": "closing odds only exist from 2019-20",
        "odds_away": "closing odds only exist from 2019-20",
        "home_shots": "shots recorded from 2000-01",
        "referee_raw": "needed for the referee factor",
    }
    for col in [
        "home_fouls",
        "away_fouls",
        "home_yellows",
        "away_yellows",
        "home_reds",
        "away_reds",
        "referee_raw",
        "home_shots",
        "home_corners",
        "odds_home",
        "odds_draw",
        "odds_away",
    ]:
        if col not in df.columns:
            continue
        filled = int(df[col].notna().sum())
        pct = filled / len(df) * 100
        print(f"  {col:<24}{filled:>10,}{pct:>7.1f}%   {notes.get(col, '')}")


def _samples(df: pd.DataFrame) -> None:
    print("\n## SAMPLE SIZES, CURRENT SQUAD (last 3 seasons)\n")
    recent = df[df["season"] >= sorted(df["season"].unique())[-3]]
    counts: dict[str, int] = {}
    for col in ("home_team_raw", "away_team_raw"):
        for team, n in recent[col].value_counts().items():
            counts[team] = counts.get(team, 0) + int(n)

    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    thin = [t for t, n in ranked if n < RELIABLE_MATCHES]
    print(f"  Teams with {RELIABLE_MATCHES}+ matches   {len(ranked) - len(thin)} of {len(ranked)}")
    if thin:
        print(f"  Thin teams              {', '.join(f'{t} ({counts[t]})' for t in thin)}")

    refs = recent["referee_raw"].value_counts()
    print(f"  Referees with 20+       {int((refs >= 20).sum())} of {len(refs)}")
    print(f"  Median referee matches  {int(refs.median())}")


def _reliability(df: pd.DataFrame) -> None:
    print("\n## IS IT ENOUGH?\n")
    per_season = df.groupby("season")["total_fouls"].agg(["count", "mean", "std"])
    recent = per_season.tail(5)
    print("  Match totals, last 5 seasons:")
    for season, row in recent.iterrows():
        print(
            f"    {season}   n={int(row['count'])}   mean={row['mean']:.2f}   sd={row['std']:.2f}"
        )

    print("\n  Verdict:")
    print(f"    MATCH level   {len(df):,} matches over {df['season'].nunique()} seasons.")
    print("                  Ample. The champion beats baseline out-of-sample.")
    print("    PLAYER level  0 rows. We hold NO player data of any kind.")
    print("                  Player markets cannot be modelled until this is fixed.")


def _missing() -> None:
    print("\n## WHAT WE DO NOT HAVE\n")
    gaps = [
        ("Per-player fouls committed", "blocks every player market"),
        ("Per-player fouls drawn", "blocks every player market"),
        ("Per-player minutes and lineups", "expected minutes is the biggest single driver"),
        ("Possession", "team style signal, not currently obtainable free"),
        ("Tackles, duels, take-ons", "the mechanical driver of fouls"),
        ("Bookmaker odds for player markets", "no free source exists, so no value claims"),
        ("Pitch location of fouls", "needs event data, free only for 2015-16"),
    ]
    for what, why in gaps:
        print(f"  {what:<38} {why}")
    print("\n  Everything above needs a per-player match data source.")
    print("  See docs/02-data-sources.md and docs/12-risks-and-open-questions.md.")


if __name__ == "__main__":
    audit()
