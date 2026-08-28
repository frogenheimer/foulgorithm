"""Current-season league leaders, from the Premier League's own API.

The foul history ends September 2025, so a leaderboard built from it would show
last season's names. This is live: it updates as the season plays out and is the
context rail on the home page.

Ranked endpoints return season totals per player for fouls, fouls won and
cards. Verified available for the current season.
"""

from __future__ import annotations

from dataclasses import dataclass

from foulgorithm.sources.base import SourceError
from foulgorithm.sources.pulselive import _get, current_season_id

# Ranked stat names the API exposes that we care about.
STATS = {
    "fouls": "Fouls committed",
    "was_fouled": "Fouls won",
    "yellow_card": "Yellow cards",
    "total_tackle": "Tackles",
}


@dataclass(frozen=True)
class Leader:
    player: str
    team: str
    value: float
    rank: int


def leaders(stat: str, season_id: int | None = None, limit: int = 10) -> list[Leader]:
    if stat not in STATS:
        raise SourceError(f"unknown stat {stat!r}. Known: {sorted(STATS)}")
    season = season_id or current_season_id()
    data = _get(f"stats/ranked/players/{stat}?compSeasons={season}&comps=1&pageSize={limit}")
    content = (data.get("stats") or {}).get("content") or []
    out = []
    for i, row in enumerate(content, start=1):
        owner = row.get("owner") or {}
        name = owner.get("name") or {}
        club = owner.get("currentTeam") or {}
        out.append(
            Leader(
                player=name.get("display", "") if isinstance(name, dict) else str(name),
                team=club.get("name", "") if isinstance(club, dict) else "",
                value=float(row.get("value") or 0),
                rank=i,
            )
        )
    return out


def all_leaders(limit: int = 8) -> dict[str, dict]:
    """Every tracked stat, with its label, ready for the site."""
    season = current_season_id()
    out = {}
    for stat, label in STATS.items():
        try:
            rows = leaders(stat, season, limit)
        except Exception as exc:  # noqa: BLE001 - reported, never silently empty
            print(f"  league leaders unavailable for {stat}: {exc}")
            continue
        if rows:
            out[stat] = {
                "label": label,
                "leaders": [
                    {"player": r.player, "team": r.team, "value": r.value, "rank": r.rank}
                    for r in rows
                ],
            }
    return out
