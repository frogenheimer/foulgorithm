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
    "interception_won",
    "interceptions_in_box",
    "total_clearance",
    "effective_clearance",
    "head_clearance",
    "effective_head_clearance",
    "clearance_off_line",
    "ball_recovery",
    # Losing the ball, which is what invites the counter-pressing foul.
    "poss_lost_all",
    "poss_lost_ctrl",
    "losses",
    "unsuccessful_touch",
    "touches_in_final_third",
    # Blocking. Weaker link to fouling than the rest, kept because the marginal
    # cost of one more stat is one request per season.
    "outfielder_block",
    "blocked_cross",
    "effective_blocked_cross",
    "blocked_pass",
    "blocked_scoring_att",
    "att_ibox_blocked",
    "att_obox_blocked",
)

#: Available at player level and deliberately NOT fetched, recorded so the next
#: person does not have to rediscover them. 158 stats respond in total; these
#: are the roughly 120 left, almost entirely passing and shooting.
#:
#: They were skipped on relevance, not cost: a foul model has little use for
#: `accurate_back_zone_pass` or `att_obox_blocked`. Adding any of them is one
#: `backfill_stats()` run, about a minute per stat across all seasons.
#:
#: Groups, by how they looked in the sweep of 2026-08-24:
#:   passing   ~36  total_pass, accurate_pass, fwd_pass, long_pass_own_to_opp,
#:                  total_final_third_passes, passes_left, crosses_18yard, ...
#:   shooting  ~68  att_ibox_target, total_scoring_att, goals_conceded_ibox,
#:                  attempts_conceded_obox, big_chance_missed, ...
#:   other     ~46  final_third_entries, pen_area_entries, wins, formation_used,
#:                  total_offside, goals, appearances_sub, ...
#:
#: The two most plausible future additions, if a model wants attacking volume:
#: `final_third_entries` and `pen_area_entries`.
FUTURE_STATS_NOTE = "see docs/28-foul-data-sources.md"


def source_url(stat: str, season_id: int) -> str:
    return (
        f"{pulselive.BASE}/stats/ranked/players/{stat}"
        f"?comps={pulselive.COMPETITION}&compSeasons={season_id}&pageSize={PAGE_SIZE}"
    )


def _short(label: str) -> str:
    """"2026/2027" to "2026/27", matching how every other season is written."""
    if "/" in label:
        start, _, end = label.partition("/")
        if len(end) == 4:
            return f"{start}/{end[2:]}"
    return label


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
            # The current season is labelled in full, "... Season 2026/2027",
            # while every other season reads "2024/25". Normalised here so one
            # season does not sort and group differently from the other twenty.
            out.append((_short(label.split()[-1]), int(row["id"])))
    return out


def fetch_stat(stat: str, season_id: int) -> dict[str, float]:
    """One stat for one season, keyed by player name. Reads EVERY page.

    A single page at `pageSize=500` silently truncates any stat more than 500
    players hold, and minutes is exactly such a stat: 537 players featured in
    2021/22 and the last 37 vanished. That truncation is why "absent from the
    fouls table" could not be read as "zero fouls". The loop is bounded by the
    API's own page count, so a season that fits one page still costs one call.
    """
    out: dict[str, float] = {}
    page = 0
    while True:
        payload = pulselive._get(
            f"stats/ranked/players/{stat}?comps={pulselive.COMPETITION}"
            f"&compSeasons={season_id}&pageSize={PAGE_SIZE}&page={page}"
        )
        block = payload.get("stats") or {}
        content = block.get("content") or []
        for row in content:
            owner = row.get("owner") or {}
            name = ((owner.get("name") or {}).get("display") or "").strip()
            if name:
                out[name] = float(row.get("value") or 0)

        info = block.get("pageInfo") or payload.get("pageInfo") or {}
        pages = int(info.get("numPages") or 1)
        page += 1
        if page >= pages or not content:
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


def backfill_stats(root: Path = CACHE, stats: tuple[str, ...] = STATS) -> dict:
    """Add stats missing from season files already on disk.

    Re-fetching whole seasons to add a column costs an hour; fetching only what
    is absent costs a few minutes. Files record which stats they hold, so the
    difference is knowable rather than guessed.
    """
    root.mkdir(parents=True, exist_ok=True)
    touched = 0

    for path in sorted(root.glob("*.json")):
        held = json.loads(path.read_text())
        have = set(held.get("stats") or [])
        missing = [s for s in stats if s not in have]
        if not missing:
            continue

        season_id = held["seasonId"]
        by_player = {row["player"]: row for row in held["players"]}
        added = 0
        for stat in missing:
            try:
                values = fetch_stat(stat, int(season_id))
            except Exception as exc:  # noqa: BLE001 - reported, never silent
                print(f"  {held['season']} {stat}: {exc}")
                continue
            for name, row in by_player.items():
                row[stat] = values.get(name)
            # A player only in the NEW stat still belongs in the file.
            for name, value in values.items():
                if name not in by_player:
                    by_player[name] = {
                        "player": name,
                        "season": held["season"],
                        "seasonId": season_id,
                        stat: value,
                    }
            added += 1

        if added:
            held["players"] = list(by_player.values())
            held["rows"] = len(held["players"])
            held["stats"] = sorted(have | set(missing))
            held["backfilledAt"] = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            path.write_text(json.dumps(held, separators=(",", ":")))
            touched += 1
            print(f"  {held['season']:<10}+{added} stats, {held['rows']} players")

    return {"seasons_updated": touched}


def repair_truncated(root: Path = CACHE, page_size: int = PAGE_SIZE) -> dict:
    """Refetch the stats the capped fetch cut short, and only those.

    A non-null count sitting exactly at the old page cap is the fingerprint of
    truncation: real season counts land on the cap about never. Refetching all
    twenty seasons costs forty minutes; refetching the fingerprinted stats
    costs a few. Merging follows `backfill_stats`: existing players gain the
    corrected value, players the cap cut off entirely join the file.
    """
    repaired, refetched = 0, 0

    for path in sorted(root.glob("*.json")):
        held = json.loads(path.read_text())
        players = held["players"]
        suspect = [
            stat
            for stat in held.get("stats") or []
            if sum(1 for row in players if row.get(stat) is not None) == page_size
        ]
        if not suspect:
            continue

        by_player = {row["player"]: row for row in players}
        fixed = 0
        for stat in suspect:
            try:
                values = fetch_stat(stat, int(held["seasonId"]))
            except Exception as exc:  # noqa: BLE001 - reported, never silent
                print(f"  {held['season']} {stat}: {exc}")
                continue
            for name, row in by_player.items():
                if name in values:
                    row[stat] = values[name]
            for name, value in values.items():
                if name not in by_player:
                    # A player the cap cut off entirely. He gets every stat the
                    # file holds, None where the league did not rank him, so a
                    # repaired row reads exactly like an assembled one.
                    by_player[name] = {
                        "player": name,
                        "season": held["season"],
                        "seasonId": held["seasonId"],
                        **{s: None for s in held.get("stats") or []},
                        stat: value,
                    }
            fixed += 1

        if fixed:
            held["players"] = list(by_player.values())
            held["rows"] = len(held["players"])
            held["repairedAt"] = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )
            path.write_text(json.dumps(held, separators=(",", ":")))
            repaired += 1
            refetched += fixed
            print(f"  {held['season']:<10}refetched {fixed} truncated stats, {held['rows']} players")

    return {"seasons_repaired": repaired, "stats_refetched": refetched}


def main() -> None:
    import sys

    if "--backfill" in sys.argv:
        print(backfill_stats())
        return
    if "--repair" in sys.argv:
        print(repair_truncated())
        return
    result = fetch_all()
    print()
    print(f"written {len(result['written'])} seasons, "
          f"skipped {len(result['skipped'])} already held, "
          f"{len(result['empty'])} with no player data")


if __name__ == "__main__":
    main()
