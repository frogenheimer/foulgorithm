"""Season-to-date totals per player, from the league's own ranked stat tables.

This is the only free route to player fouls that is still live. The
worldfootballR archive stops in September 2025, and FBref lost its Opta feed in
January 2026, so nothing else fills the gap.

The shape is awkward and worth stating plainly: the league publishes per-fixture
stats at TEAM level, and per-player stats only as SEASON TOTALS. A player's
fouls in one match are therefore recoverable as the difference between two
snapshots, and not otherwise. See foulgorithm.jobs.settle.

Players on zero are omitted from the tables rather than listed, so an absent
name means zero and not unknown.
"""

from __future__ import annotations

from foulgorithm.sources import pulselive

# The three we need. `appearances` is not optional: without it a difference
# cannot be attributed to a single match.
STATS = ("fouls", "was_fouled", "appearances")


def _ranked(stat: str, season_id: int, page_size: int = 100) -> dict[str, float]:
    out: dict[str, float] = {}
    page = 0
    while True:
        payload = pulselive._get(
            f"stats/ranked/players/{stat}?comps={pulselive.COMPETITION}"
            f"&compSeasons={season_id}&pageSize={page_size}&page={page}"
        )
        block = payload.get("stats") or {}
        for entry in block.get("content") or []:
            owner = entry.get("owner") or {}
            name = (owner.get("name") or {}).get("display")
            if name:
                out[name] = float(entry.get("value") or 0.0)
        info = block.get("pageInfo") or {}
        page += 1
        if page >= float(info.get("numPages") or 1):
            return out


def season_totals(season_id: int | None = None) -> dict[str, dict[str, float]]:
    """Every player with a non-zero total, keyed by display name."""
    season_id = season_id or pulselive.current_season_id()
    tables = {stat: _ranked(stat, season_id) for stat in STATS}
    players = set().union(*tables.values())
    return {
        name: {stat: tables[stat].get(name, 0.0) for stat in STATS}
        for name in sorted(players)
    }
