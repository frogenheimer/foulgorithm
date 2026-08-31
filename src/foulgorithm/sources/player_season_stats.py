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

# `appearances` is not optional: without it a difference cannot be attributed
# to a single match. `mins_played` makes a settled match a full training row
# rather than half of one; these rows are the only per-match player data this
# season will ever have.
#
# Cards ride along from docs/48: the card study needs this season's bookings
# per match, and a booking not snapshotted the week it happened is not
# recoverable later, because the league only ever publishes running totals.
# Fetching them costs two more paginated reads a settle run and commits us to
# nothing: nothing is graded or published on a card until the gate passes.
STATS = ("fouls", "was_fouled", "appearances", "mins_played", "yellow_card", "red_card")


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


#: Without these a difference cannot be attributed to a match at all, so an
#: empty table for one of them is a dead source and stops the run.
REQUIRED = ("fouls", "was_fouled", "appearances")


class SourceShapeError(RuntimeError):
    """A stat table the whole job depends on came back empty."""


def season_totals(season_id: int | None = None) -> dict[str, dict[str, float]]:
    """Every player with a non-zero total, keyed by display name.

    A stat whose table comes back EMPTY is omitted rather than written as
    zero for everybody. Players on zero are absent from a populated table,
    so "absent" normally means zero, but a table with nobody in it means the
    endpoint moved. Written as zeros that would say "nobody was booked"
    every week, quietly and forever, since nothing is published on a card
    yet to make it visible. Omitted, it reads as unknown (see
    `settle._rider`), which is the honest answer and self-healing: the week
    the table returns, the stat resumes.

    An empty REQUIRED table is not survivable and raises.
    """
    season_id = season_id or pulselive.current_season_id()
    tables = {stat: _ranked(stat, season_id) for stat in STATS}
    empty = [stat for stat, table in tables.items() if not table]
    dead = [stat for stat in empty if stat in REQUIRED]
    if dead and any(tables.values()):
        raise SourceShapeError(
            f"{', '.join(dead)} came back with no players while other tables have some. "
            "That is a changed endpoint, not a quiet week, and settling against it "
            "would grade a whole round as zero."
        )
    live = [stat for stat in STATS if stat not in empty]
    players = set().union(*tables.values())
    return {name: {stat: tables[stat].get(name, 0.0) for stat in live} for name in sorted(players)}
