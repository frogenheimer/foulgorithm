"""Player season totals from the league itself, every season back to 2006/07.

The league publishes per-player totals through `stats/ranked/players/{stat}`,
and that endpoint takes a season. Twenty complete seasons are available, which
is eleven further back than our match archive reaches and covers both of its
gaps. See `docs/28-foul-data-sources.md` for how this was established.

**Season totals, not per-match.** A single match is only recoverable by
differencing two snapshots, and the API has no as-of-date: every gameweek filter
it accepts is silently discarded. So this completes player RATES for twenty
years and adds no per-match rows, which given the player's own rate is the
largest input to a prediction is a good trade.

Fetched once and written to disk with provenance, because the last source we
relied on froze for eleven months without anyone noticing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from foulgorithm.sources import pulselive

CACHE = Path("data/raw/pulselive/player_seasons")

#: The whole season in one request. At the default of 100 this would take five
#: times as many calls for exactly the same data.
PAGE_SIZE = 500

#: The first season the league carries player fouls for. 2005/06 and earlier
#: return zero players, verified season by season.
FIRST_SEASON = "2006/07"

#: What to pull. Every one verified to respond at player level.
#:
#: `attempted_tackle_foul` is the interesting one: a tackle attempt that became
#: a foul, which is close to the mechanism being modelled and something no
#: source we had before carried.
STATS: tuple[str, ...] = (
    # Denominators. A count without these cannot become a rate.
    "mins_played",
    "appearances",
    "touches",
    # The two markets, and where they happen.
    "fouls",
    "was_fouled",
    "fouled_final_third",
    # Discipline.
    "yellow_card",
    "red_card",
    "penalty_conceded",
    # Tackling, the mechanism.
    "total_tackle",
    "won_tackle",
    "attempted_tackle_foul",
    "challenge_lost",
    # Duels.
    "duel_won",
    "duel_lost",
    "aerial_won",
    "aerial_lost",
    # Carrying, which is what draws fouls.
    "total_contest",
    "won_contest",
    "dispossessed",
    # Where on the pitch a player operates.
    "poss_won_def_3rd",
    "poss_won_mid_3rd",
    "poss_won_att_3rd",
    "touches_in_opp_box",
    # Defending.
    "interception",
    "total_clearance",
    "ball_recovery",
)


def source_url(stat: str, season_id: int) -> str:
    return (
        f"{pulselive.BASE}/stats/ranked/players/{stat}"
        f"?comps={pulselive.COMPETITION}&compSeasons={season_id}&pageSize={PAGE_SIZE}"
    )


def seasons() -> list[tuple[str, int]]:
    """Every season the league exposes, newest first, label and id."""
    payload = pulselive._get(
        f"competitions/{pulselive.COMPETITION}/compseasons?pageSize=50"
    )
    out = []
    for row in payload.get("content") or []:
        label = row.get("label")
        if label and "/" in label:
            out.append((label, int(row["id"])))
        elif label and "Season" in label:
            # The current season is labelled in full: "... Season 2026/2027".
            out.append((label.split()[-1], int(row["id"])))
    return out


def fetch_stat(stat: str, season_id: int) -> dict[str, float]:
    """One stat for one season, keyed by player name."""
    payload = pulselive._get(
        f"stats/ranked/players/{stat}?comps={pulselive.COMPETITION}"
        f"&compSeasons={season_id}&pageSize={PAGE_SIZE}&page=0"
    )
    out: dict[str, float] = {}
    for row in ((payload.get("stats") or {}).get("content") or []):
        owner = row.get("owner") or {}
        name = ((owner.get("name") or {}).get("display") or "").strip()
        if name:
            out[name] = float(row.get("value") or 0)
    return out


def assemble(label: str, season_id: int, raw: dict[str, dict[str, float]]) -> list[dict]:
    """One row per player, every stat on it.

    A player absent from a stat gets None rather than zero. Zero fouls and
    unrecorded fouls are different facts and collapsing them would quietly
    invent a perfect disciplinary record for anyone the league did not rank.
    """
    everyone: set[str] = set()
    for values in raw.values():
        everyone.update(values)

    return [
        {
            "player": name,
            "season": label,
            "seasonId": season_id,
            **{stat: raw.get(stat, {}).get(name) for stat in raw},
        }
        for name in sorted(everyone)
    ]


def write_season(
    root: Path, label: str, season_id: int, rows: list[dict], stats: tuple[str, ...]
) -> Path | None:
    """Write one season, with where it came from and when.

    An empty season is not written. A file of nothing looks identical to a
    season nobody tried, and the difference matters when the next person is
    working out whether a gap is real.
    """
    if not rows:
        return None

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{label.replace('/', '-')}.json"
    path.write_text(
        json.dumps(
            {
                "season": label,
                "seasonId": season_id,
                "source": source_url(stats[0], season_id),
                "fetchedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "stats": list(stats),
                "rows": len(rows),
                "players": rows,
            },
            separators=(",", ":"),
        )
    )
    return path


def fetch_all(root: Path = CACHE, stats: tuple[str, ...] = STATS) -> dict:
    """Every season the league carries, one file each. Skips what is already held."""
    root.mkdir(parents=True, exist_ok=True)
    written, skipped, empty = [], [], []

    for label, season_id in seasons():
        path = root / f"{label.replace('/', '-')}.json"
        if path.exists():
            skipped.append(label)
            continue

        raw = {}
        for stat in stats:
            try:
                raw[stat] = fetch_stat(stat, season_id)
            except Exception as exc:  # noqa: BLE001 - reported per stat, never silent
                print(f"  {label} {stat}: {exc}")
                raw[stat] = {}

        rows = assemble(label, season_id, raw)
        if write_season(root, label, season_id, rows, stats):
            written.append((label, len(rows)))
            print(f"  {label:<10}{len(rows):>4} players")
        else:
            empty.append(label)

    return {"written": written, "skipped": skipped, "empty": empty}


def main() -> None:
    result = fetch_all()
    print()
    print(f"written {len(result['written'])} seasons, "
          f"skipped {len(result['skipped'])} already held, "
          f"{len(result['empty'])} with no player data")


if __name__ == "__main__":
    main()
