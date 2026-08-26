"""Per-player foul rates for BOTH divisions.

**This module exists because a claim we had written down was wrong.**
`features/promotion.py` has said since it was written that "Championship player
data does not exist at any price", `docs/02` repeated it, and the cup pages were
built around it. The Premier League's own API carries ranked player stats for
competition 12 as well as competition 1: fouls, fouls won, tackles, cards,
appearances and minutes, for 681 Championship players. Free, no key, and on a
source this project already depends on.

The shape is the same awkward one `docs/02` already describes for the top
flight, and it is worth restating rather than discovering again:

  **These are TOTALS, not per-match rows.** A rate is `total / (minutes / 90)`,
  which is enough to PUBLISH and not enough to TRAIN on. A player's fouls in one
  match are recoverable only by differencing two snapshots either side of it,
  which works going forward and cannot be done backwards. See jobs/settle.

So this feeds the cup pages' player tables and nothing else. Picks stay where
the per-match history is.

One sweep per stat covers a whole division, so the cost is six requests a
division rather than one per player, and a cup tie costs nothing beyond the
cache.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from foulgorithm.identity.teams import to_fixture_name
from foulgorithm.sources import pulselive

CACHE = Path("data/raw")

#: How long a sweep stays fresh. These move when a match is played, and the
#: cup pages republish on the same schedule, so half a day is plenty and keeps
#: a local run instant.
MAX_AGE_SECONDS = 12 * 3600

#: Our division codes to the league API's competition ids. E0 is the Premier
#: League, E1 the Championship, matching football-data.co.uk's own file names
#: so one vocabulary runs from the CSVs through to here.
COMPETITIONS = {"E0": 1, "E1": 12}

#: Every stat a player row carries. `mins_played` is not optional: without it
#: a total is a count rather than a rate, and a count flatters whoever played
#: most. `appearances` is what tells a reader how thin a rate is.
STATS = (
    "fouls",
    "was_fouled",
    "total_tackle",
    "yellow_card",
    "red_card",
    "appearances",
    "mins_played",
)

#: Below this many minutes a rate is mostly noise. Flagged, never hidden: a
#: reader who can see "180 minutes" discounts the number himself.
THIN_MINUTES = 450.0


DIVISION_NAMES = {"E0": "Premier League", "E1": "Championship"}


@dataclass(frozen=True)
class PlayerStats:
    player: str
    player_id: int
    club: str
    position: str
    shirt: int | None

    appearances: int
    minutes: float
    fouls: int
    fouls_won: int
    tackles: int
    yellows: int
    reds: int

    fouls_per_90: float | None
    fouls_won_per_90: float | None
    tackles_per_90: float | None

    #: Minutes per division, so a pooled rate can say where it came from.
    minutes_by_division: dict[str, float] | None = None

    @property
    def thin(self) -> bool:
        return self.minutes < THIN_MINUTES

    def spell_label(self) -> str:
        """"900 minutes in the Premier League, 450 in the Championship".

        A player's record follows him rather than his club. Wolves came down
        and their squad's minutes are top-flight ones; Wrexham went up and
        theirs are second-tier. Pooling is right and pooling silently is not.
        """
        by = self.minutes_by_division or {}
        parts = [
            f"{int(by[d])} minutes in the {DIVISION_NAMES[d]}" if i == 0
            else f"{int(by[d])} in the {DIVISION_NAMES[d]}"
            for i, d in enumerate(d for d in ("E0", "E1") if by.get(d))
        ]
        return ", ".join(parts) if parts else "No minutes on record"


def sweep(
    competition: int,
    stat: str,
    page_size: int = 100,
    api=pulselive,
    cache_root: Path | None = None,
    force: bool = False,
) -> dict[int, dict]:
    """One ranked table, keyed by player id.

    Keyed by id rather than by name, unlike the older
    `sources/player_season_stats`. Two players can share a display name (there
    are two Reece Jameses in these two divisions alone) and the team sheets
    this gets joined to carry ids, so a name key would both collide and fail to
    join.

    No `compSeasons` filter. With one, the endpoint returns nothing for
    competition 12; without one it returns a player's totals within that
    competition, which is a bigger sample and the more honest figure to show
    beside "48 appearances in the Championship".
    """
    cached = (cache_root or CACHE) / "pulselive" / f"ranked_{competition}_{stat}.json"
    if not force and _fresh(cached):
        return _read(cached)

    out: dict[int, dict] = {}
    page = 0
    try:
        while True:
            payload = api._get(
                f"stats/ranked/players/{stat}?comps={competition}"
                f"&pageSize={page_size}&page={page}"
            )
            block = payload.get("stats") or {}
            for row in block.get("content") or []:
                owner = row.get("owner") or {}
                # `id`, NEVER `playerId`. Pulselive carries two id spaces and
                # both are plausible-looking integers: Abdul Fatawu is
                # id=127644 and playerId=786120. Squad lists and team sheets
                # are keyed on `id`, so keying this on `playerId` joined to
                # nothing and every player came back with zero minutes, which
                # renders as a squad that has never played rather than as a
                # broken join.
                pid = owner.get("id")
                if pid is None:
                    continue
                info = owner.get("info") or {}
                team = owner.get("currentTeam") or {}
                shirt = info.get("shirtNum")
                out[int(pid)] = {
                    "value": float(row.get("value") or 0.0),
                    "player": (owner.get("name") or {}).get("display"),
                    "club": team.get("name"),
                    "position": info.get("position") or "?",
                    "shirt": int(shirt) if shirt is not None else None,
                }
            page += 1
            if page >= float((block.get("pageInfo") or {}).get("numPages") or 1):
                break
    except Exception as exc:  # noqa: BLE001 - stale beats gone
        if cached.exists():
            print(f"  {stat} sweep failed ({exc}), serving the cache", file=sys.stderr)
            return _read(cached)
        raise

    _write(cached, out)
    return out


def _fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < MAX_AGE_SECONDS


def _read(path: Path) -> dict[int, dict]:
    """JSON has no integer keys, and the join to a team sheet is on ints."""
    return {int(k): v for k, v in json.loads(path.read_text()).items()}


def _write(path: Path, rows: dict[int, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, separators=(",", ":")))


def squad_ids(competition: int, api=pulselive, cache_root: Path | None = None,
              force: bool = False) -> dict[str, list[int]]:
    """Who is actually in each club's squad this season, by player id.

    Membership has to come from here and not from the ranked tables. A ranked
    row's `currentTeam` is the player's LAST club, so reading membership off it
    put Petr Cech in Arsenal's 2026/27 squad seven years after he retired.

    One request for the competition's clubs, then one per club. Cached, so a
    site build spends nothing.
    """
    cached = (cache_root or CACHE) / "pulselive" / f"squads_{competition}.json"
    if not force and _fresh(cached):
        return {k: [int(i) for i in v] for k, v in json.loads(cached.read_text()).items()}

    try:
        return _fetch_squads(competition, api, cached)
    except Exception as exc:  # noqa: BLE001 - stale beats gone
        if cached.exists():
            print(f"  squad list failed ({exc}), serving the cache", file=sys.stderr)
            return {k: [int(i) for i in v] for k, v in json.loads(cached.read_text()).items()}
        raise


def _fetch_squads(competition: int, api, cached: Path) -> dict[str, list[int]]:
    seasons = api._get(f"competitions/{competition}/compseasons?pageSize=2")
    season = int((seasons.get("content") or [{}])[0].get("id"))

    teams = api._get(
        f"teams?pageSize=50&comps={competition}&compSeasons={season}&altIds=true&page=0"
    )
    out: dict[str, list[int]] = {}
    for team in teams.get("content") or []:
        tid = team.get("id")
        name = team.get("name")
        if tid is None or not name:
            continue
        squad = api._get(
            f"players?pageSize=80&teams={int(tid)}&compSeasons={season}&page=0"
        )
        ids = [
            int(p["id"]) for p in (squad.get("content") or []) if p.get("id") is not None
        ]
        if ids:
            out[name] = ids

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(out, separators=(",", ":")))
    return out


def _rate(total: float, minutes: float) -> float | None:
    """Per ninety. None when nobody has played, because a rate over no time is
    not zero, it is undefined."""
    if not minutes:
        return None
    return round(total / (minutes / 90.0), 2)


def squads(
    division: str, api=pulselive, cache_root: Path | None = None, force: bool = False
) -> dict[str, list[PlayerStats]]:
    """Every club's players in one division, busiest first.

    Raises on a division we do not hold, rather than returning an empty dict
    that reads like a club with no players.
    """
    competition = COMPETITIONS[division]
    tables = {
        stat: sweep(competition, stat, api=api, cache_root=cache_root, force=force)
        for stat in STATS
    }

    # A ranked table omits players on zero rather than listing them, so the
    # roster is the union and an absent id means zero, not unknown.
    ids: set[int] = set()
    for table in tables.values():
        ids |= set(table)

    out: dict[str, list[PlayerStats]] = {}
    for pid in ids:
        meta = next((tables[s][pid] for s in STATS if pid in tables[s]), None)
        if meta is None or not meta.get("club"):
            continue

        def total(stat: str) -> float:
            row = tables[stat].get(pid)
            return row["value"] if row else 0.0

        minutes = total("mins_played")
        out.setdefault(meta["club"], []).append(
            PlayerStats(
                player=meta["player"],
                player_id=pid,
                club=meta["club"],
                position=meta["position"],
                shirt=meta["shirt"],
                appearances=int(total("appearances")),
                minutes=minutes,
                fouls=int(total("fouls")),
                fouls_won=int(total("was_fouled")),
                tackles=int(total("total_tackle")),
                yellows=int(total("yellow_card")),
                reds=int(total("red_card")),
                fouls_per_90=_rate(total("fouls"), minutes),
                fouls_won_per_90=_rate(total("was_fouled"), minutes),
                tackles_per_90=_rate(total("total_tackle"), minutes),
            )
        )

    for players in out.values():
        players.sort(key=lambda p: (-p.minutes, p.player))
    return out


def for_clubs(
    clubs: list[str], api=pulselive, cache_root: Path | None = None, force: bool = False
) -> dict[str, list[PlayerStats]]:
    """Current squads for named clubs, with records pooled across BOTH divisions.

    Two authorities, kept apart on purpose. The squad list says who is THERE;
    the ranked tables say what they have DONE. Conflating them put a retired
    goalkeeper in this season's Arsenal squad.

    Sweeping only the division a club is in today is the other trap: Wolves
    came down and their squad's minutes are Premier League ones, filed under
    competition 1. A player's record follows him, not his club.
    """
    wanted = set(clubs)

    # Who is in each squad, and which of our clubs they belong to.
    roster: dict[int, str] = {}
    for competition in COMPETITIONS.values():
        squads = (
            api.squad_ids(competition)
            if hasattr(api, "squad_ids")
            else squad_ids(competition, api=api, cache_root=cache_root, force=force)
        )
        for raw_club, ids in squads.items():
            club = to_fixture_name(raw_club) or raw_club
            if club not in wanted:
                continue
            for pid in ids:
                roster[int(pid)] = club

    merged: dict[int, dict] = {}
    for division, competition in COMPETITIONS.items():
        tables = {
            stat: sweep(competition, stat, api=api, cache_root=cache_root, force=force)
            for stat in STATS
        }
        for pid, club in roster.items():
            meta = next((tables[s][pid] for s in STATS if pid in tables[s]), None)
            row = merged.setdefault(
                pid,
                {"meta": meta, "club": club, "totals": dict.fromkeys(STATS, 0.0),
                 "minutes_by_division": {}},
            )
            if row["meta"] is None and meta is not None:
                row["meta"] = meta
            for stat in STATS:
                found = tables[stat].get(pid)
                if found:
                    row["totals"][stat] += found["value"]
            minutes = (tables["mins_played"].get(pid) or {}).get("value") or 0.0
            if minutes:
                row["minutes_by_division"][division] = minutes

    out: dict[str, list[PlayerStats]] = {club: [] for club in clubs}
    for pid, row in merged.items():
        totals = row["totals"]
        # A summer signing with no minutes anywhere has no ranked row at all.
        # He is still in the squad, so he is still on the page, with blanks.
        meta = row["meta"] or {"player": None, "position": "?", "shirt": None}
        minutes = totals["mins_played"]
        out[row["club"]].append(
            PlayerStats(
                player=meta.get("player") or f"Player {pid}",
                player_id=pid,
                club=row["club"],
                position=meta.get("position") or "?",
                shirt=meta.get("shirt"),
                appearances=int(totals["appearances"]),
                minutes=minutes,
                fouls=int(totals["fouls"]),
                fouls_won=int(totals["was_fouled"]),
                tackles=int(totals["total_tackle"]),
                yellows=int(totals["yellow_card"]),
                reds=int(totals["red_card"]),
                fouls_per_90=_rate(totals["fouls"], minutes),
                fouls_won_per_90=_rate(totals["was_fouled"], minutes),
                tackles_per_90=_rate(totals["total_tackle"], minutes),
                minutes_by_division=row["minutes_by_division"],
            )
        )

    for players in out.values():
        players.sort(key=lambda p: (-p.minutes, p.player))
    return out
