"""Match history for both divisions, tagged with where each row came from.

`sources.football_data` fetches one season file at a time and does not care
which division it is. This adds the two things everything downstream needs: the
season and the division stamped onto every row, and a per-tie loader that reads
each division file once no matter how many clubs from it are involved.

A season file that does not exist yet is skipped with a note, never raised. In
August the current E1 file may be days old or absent, and one missing season
must not take a cup page down.
"""

from __future__ import annotations

from datetime import datetime, timezone

from foulgorithm.identity.teams import CHAMPIONSHIP, PREMIER
from foulgorithm.sources import football_data

#: The published window: this season and last. Matches the league team pages,
#: which run on the same two seasons, and is long enough that a club three
#: games into a season is not being read off three games.
SEASONS_BACK = 1


def default_seasons(now_year: int | None = None, now_month: int | None = None) -> list[str]:
    """Season labels for the window, oldest first.

    A season starting in August of year Y is labelled Y-(Y+1), so anything
    before August still belongs to the season that started the previous year.
    """
    now = datetime.now(timezone.utc)
    year = now_year if now_year is not None else now.year
    month = now_month if now_month is not None else now.month
    current = year if month >= 8 else year - 1
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(current - SEASONS_BACK, current + 1)]


def load(seasons: list[str], division: str, source=football_data) -> list[dict]:
    """Every match in one division across the given seasons, season-tagged."""
    rows: list[dict] = []
    for label in seasons:
        try:
            parsed = source.parse(source.fetch(label, division=division))
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            print(f"  skipped {label} {division}: {exc}")
            continue
        for row in parsed:
            row["season"] = label
            row["division"] = division
        rows.extend(parsed)
    return rows


def window(
    seasons: list[str] | None = None,
    source=football_data,
) -> dict[str, list[dict]]:
    """Every match in BOTH divisions across the window, keyed by division.

    Both, always, and not just the division a club is in today. Burnley played
    2025-26 in the Premier League and 2026-27 in the Championship. Loading only
    their current division would drop half their record, and would drop it
    silently: the spell label that exists to expose a crossing would never see
    one. Four cached CSVs is a cheap price for not lying about a promoted club.
    """
    seasons = seasons or default_seasons()
    return {d: load(seasons, d, source=source) for d in (PREMIER, CHAMPIONSHIP)}


def pooled(by_division: dict[str, list[dict]]) -> list[dict]:
    """One flat list. Each row still carries its own division."""
    return [row for division in by_division.values() for row in division]
