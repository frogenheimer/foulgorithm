"""Turn published predictions into a graded record.

The grading job has existed since the start and nothing built the outcomes it
needs, so nothing was ever actually graded. This closes that.

**Why it works by subtraction.** The league publishes per-fixture stats at TEAM
level and per-player stats only as season totals, so a player's fouls in one
match are the difference between two weekly snapshots and are not available any
other way. The worldfootballR archive stops in September 2025 and FBref lost its
Opta feed in January 2026, so there is no cleaner source to switch to.

**Where it refuses.** A difference is only attributable to one match when the
player made exactly one appearance between snapshots. In a midweek round he may
have made two, and then the difference is a sum whose parts are unknowable.
Those are left ungraded and counted, rather than split on an assumption, because
a public track record built partly on invented numbers is worse than a shorter
one.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Committed, not cached. See lineup_watch.STATE for why. It matters more here:
# with no previous snapshot, per_match() diffs against nothing and a player's
# whole SEASON total is graded as one match's outcome.
SNAPSHOT = Path("data/state/player_season_totals.json")
TRACK_RECORD = Path("site/public/data/track-record.json")

MARKETS = {"fouls": "player_fouls_committed", "was_fouled": "player_fouls_drawn"}

# How long after a kickoff the league's player totals can still be moving.
#
# MEASURED, not guessed: docs/53-posting-latency.md. Five kickoff slots over
# the 28 to 30 August matchdays, polled every ten minutes. The tables climb
# from about twenty minutes into a match and go still within ten minutes of
# full time; the worst slot took 2h05 from kickoff. This sits 25 minutes
# clear of that, which is 15 clear once the poll granularity is allowed for.
#
# Not shared with `store.players.STATS_DELAY`, which stamps `known_at` on
# historical archive rows from a different feed that this never measured.
STATS_DELAY = timedelta(hours=2, minutes=30)


def per_match(before: dict, after: dict) -> dict[str, dict[str, int]]:
    """What each player did in the single match between two snapshots.

    Players who did not feature are absent. Players who featured twice are
    absent, deliberately: see the module docstring.
    """
    out: dict[str, dict[str, int]] = {}
    for name, now in after.items():
        was = before.get(name, {})
        appearances = now.get("appearances", 0) - was.get("appearances", 0)
        if appearances < 0 or any(
            now.get(k, 0) < was.get(k, 0)
            for k in ("fouls", "was_fouled", "yellow_card", "red_card")
        ):
            raise ValueError(
                f"{name}'s season total fell between snapshots. Totals only rise, "
                "so this is a season rollover or a change of source shape, and "
                "settling against it would produce nonsense."
            )
        if appearances != 1:
            continue
        out[name] = {
            "fouls_committed": int(now.get("fouls", 0) - was.get("fouls", 0)),
            "fouls_drawn": int(now.get("was_fouled", 0) - was.get("was_fouled", 0)),
            "minutes": _rider("mins_played", now, was),
            # docs/48 step 1: the house's card record starts accruing before
            # a single card figure is published, so the study that decides
            # whether any of it is publishable has this season's rows to run on.
            "yellows": _rider("yellow_card", now, was),
            "reds": _rider("red_card", now, was),
        }
    return out


def _rider(stat: str, now: dict, was: dict) -> int | None:
    """A stat that joined the snapshot after it started: differenced, or unknown.

    Only when BOTH snapshots carry it, or the player is a debutant absent
    from the earlier one entirely. Every snapshot format predates the stat
    that joined it last, and a zero there would say a player finished last
    week on no bookings and was booked tonight, which is a lie with a
    straight face. The same rule minutes have needed since docs/35.
    """
    if stat in now and stat in was:
        return int(now[stat] - was[stat])
    if stat in now and not was:
        return int(now[stat])
    return None


SETTLED_ROWS = Path("data/settled/player_matches.jsonl")


def persist_matches(
    matches: dict, window_start: str | None, window_end: str, path: Path = SETTLED_ROWS
) -> int:
    """Keep the settled per-match rows, not just the grades they produced.

    These rows are the only per-match player data this season will ever
    have: the archive froze, the league publishes only running totals, and a
    difference consumed for grading and discarded is training data destroyed.
    Append-only, one row per player per window, and a window already on file
    is skipped whole so a rerun after a crashed snapshot write cannot double
    a round.
    """
    if not matches:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and f'"window_end": "{window_end}"' in path.read_text():
        return 0
    with path.open("a") as handle:
        for name, stats in sorted(matches.items()):
            handle.write(
                json.dumps(
                    {
                        "player": name,
                        "window_start": window_start,
                        "window_end": window_end,
                        **stats,
                    },
                    separators=(", ", ": "),
                )
                + "\n"
            )
    return len(matches)


def outcomes(matches: dict[str, dict[str, int]]) -> dict[tuple[str, str], float]:
    """Keyed the way foulgorithm.review.grade expects."""
    return {
        (name, market): float(stats[key])
        for name, stats in matches.items()
        for key, market in (
            ("fouls_committed", "player_fouls_committed"),
            ("fouls_drawn", "player_fouls_drawn"),
        )
    }


def resolve_outcomes(
    matches: dict[str, dict[str, int]], claims: list[dict], overrides: dict | None = None
) -> dict[tuple[str, str], float]:
    """Outcomes keyed by each claim's OWN entity, not the stats source's name.

    The league's season totals abbreviate ("Nico González", "Andy Robertson")
    where the squads and therefore the claims carry the fuller name. Graded
    on the raw name, 29 of the 36 legs that read as no-shows on 30 August
    were this gap, and docs/49 makes a no-show a loss, so the gap has to be
    closed first. Resolution is identity.players' rules, both token
    directions plus the human crosswalk, and a name they refuse stays
    ungraded rather than guessed (ADR-007). The raw keys stay in the map so
    a claim already on the source's spelling grades as before.
    """
    from foulgorithm.identity.players import resolve_names

    out = outcomes(matches)
    entities = sorted({c["entity"] for c in claims if c.get("entity")})
    if not entities or not matches:
        return out
    found = resolve_names(entities, list(matches), overrides=overrides).matched
    for entity, source_name in found.items():
        if entity == source_name:
            continue
        for market in ("player_fouls_committed", "player_fouls_drawn"):
            if (source_name, market) in out:
                out.setdefault((entity, market), out[(source_name, market)])
    return out


def pending_fixtures(fixtures, now=None) -> list:
    """Fixtures that have started but whose stats may not have posted yet.

    A player's fouls are the difference between two snapshots, so a snapshot
    taken while a match is half-posted does its damage later, not now: it
    becomes the next run's baseline, the fouls arrive in a window where
    appearances did not move, and the exactly-one-appearance rule discards
    them permanently. Three fixtures graded near zero this way on 22 August,
    all from the same 14:00 slot.

    The league posts in play, so this is not belt and braces: appearance
    counts rise mid-match alongside the fouls, which means a snapshot taken
    while a game is on records a valid-looking one-appearance diff carrying
    only part of that player's fouls. See `STATS_DELAY` above.
    """
    now = now or datetime.now(UTC)
    return [f for f in fixtures if f.kickoff_utc <= now and (now - f.kickoff_utc) < STATS_DELAY]


def settled_fixtures(fixtures, since: str | None) -> set[str]:
    """Fixtures this snapshot window settles, named as predictions record them.

    Complete, AND kicked off after the previous snapshot was taken. The gate
    used to be every completed game this season, and on 28 August 2026 the
    evening settle graded 141 of the previous round's still-open claims with
    that night's diffs: a player unused last week whose first outcome arrived
    tonight settled last week's claim about him. A diff can only speak for
    the games inside its own window.
    """
    from foulgorithm.identity.teams import from_pulselive

    floor = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    return {
        f"{from_pulselive(f.home)} v {from_pulselive(f.away)}"
        for f in fixtures
        if f.complete and (floor is None or f.kickoff_utc > floor)
    }


def _settled_fixtures(since: str | None = None) -> set[str]:
    from foulgorithm.sources import pulselive

    return settled_fixtures(pulselive.fixtures(), since)


PLAYERS = Path("site/public/data/players.json")


def refresh_table(path: Path = PLAYERS) -> bool:
    """Rewrite the standings and settled cards in the live payload, in place.

    Only those two blocks: the board, the picks and everything else stay
    exactly as the last publish left them. Returns False when there is no
    payload to refresh, which is a fresh checkout, not an error.
    """
    if not path.exists():
        return False
    from foulgorithm.publish import player_round

    payload = json.loads(path.read_text())
    ids = [row["id"] for row in payload.get("standings") or []]
    if not ids:
        return False
    payload["standings"] = player_round._standings(ids)
    payload["settledCards"] = player_round._settled_cards()
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return True


def regrade_from_windows(
    completed: set[str],
    claims: list[dict] | None = None,
    rows_path: Path = SETTLED_ROWS,
    graded_root: Path | None = None,
) -> int:
    """Grade any ungraded claim for a completed fixture from the rows on file.

    docs/49. The settle job grades the binding version it can see at the
    moment it runs. A version that arrives afterwards (a hand publish pushed
    late, a rebase of two histories) used to sit ungraded all season, and
    the table read it as unsettled or void. The per-match rows persisted at
    settle time are enough to grade at any time, so every table refresh
    does. Append-only and deduplicated on the claim key by the grader
    itself, so a rerun changes nothing. Returns how many claims were graded.
    """
    from foulgorithm.review import grade as grading
    from foulgorithm.store import predictions as pred_store

    if not completed or not rows_path.exists():
        return 0
    root = graded_root if graded_root is not None else grading.GRADED
    windows: dict[tuple[str | None, str], dict] = {}
    for line in rows_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row.get("window_start"), row["window_end"])
        windows.setdefault(key, {})[row["player"]] = {
            "fouls_committed": row.get("fouls_committed", 0),
            "fouls_drawn": row.get("fouls_drawn", 0),
        }
    if not windows:
        return 0

    have = {g["key"] for g in grading.load_all(root)}
    pool = claims if claims is not None else pred_store.load_all()
    pending = [c for c in pool if c.get("fixture") in completed and c.get("key") not in have]
    if not pending:
        return 0

    def _at(value: str | None):
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

    graded = 0
    for (start, end), matches in windows.items():
        opened, closed = _at(start), _at(end)
        inside = [
            c
            for c in pending
            if closed is not None
            and (kick := _at(c.get("kickoff"))) is not None
            and kick < closed
            and (opened is None or kick > opened)
        ]
        if not inside:
            continue
        result = grading.grade(resolve_outcomes(matches, inside), predictions=inside, root=root)
        graded += result["graded"]
        done = {g.key for g in result["results"]}
        pending = [c for c in pending if c.get("key") not in done]
    return graded


def run(dry_run: bool = False) -> int:
    from foulgorithm.review import grade as grading
    from foulgorithm.sources import player_season_stats
    from foulgorithm.store import predictions as pred_store

    # Before anything reads or writes a snapshot: if a match is still posting,
    # this run's reading would become the next run's baseline while half of a
    # fixture is missing from it, and those fouls are then unrecoverable. A
    # deferred run costs a few hours. See pending_fixtures.
    try:
        from foulgorithm.sources import pulselive

        waiting = pending_fixtures(pulselive.fixtures())
    except Exception as exc:  # noqa: BLE001 - reported; deciding blind is worse
        print(f"cannot check whether fixtures have posted: {exc}", file=sys.stderr)
        return 2
    if waiting:
        soonest = min(f.kickoff_utc for f in waiting)
        print(
            f"{len(waiting)} fixture(s) kicked off within the stats delay, earliest "
            f"{soonest:%Y-%m-%d %H:%M}. Deferring: snapshotting now would freeze a "
            "half-posted reading into the baseline and lose those fouls for good."
        )
        return 1

    try:
        current = player_season_stats.season_totals()
    except Exception as exc:
        print(f"season totals unavailable: {exc}", file=sys.stderr)
        return 2
    if not current:
        print("no player totals yet this season", file=sys.stderr)
        return 1

    previous = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {}
    matches = per_match(previous.get("totals", {}), current)
    if not matches:
        print(f"nothing new to settle, {len(current)} players tracked")
        return 1

    # Only grade predictions for fixtures that have actually finished.
    #
    # Without this, a prediction gets graded against whatever the latest
    # snapshot difference happens to say, because outcomes are keyed by player
    # and market with no fixture in the key. A player's Saturday appearance
    # would settle a claim about his Tuesday match. That would not fail
    # loudly; it would quietly produce a track record that looks real.
    settled = _settled_fixtures(since=previous.get("takenAt"))
    if not settled:
        print("no completed fixtures to settle against")
        return 1
    claims = [r for r in pred_store.load_all() if r["fixture"] in settled]
    if not claims:
        print(f"{len(settled)} fixtures settled, but no predictions match them")
        return 1

    result = grading.grade(resolve_outcomes(matches, claims), predictions=claims)
    summary = grading.summarise(result["results"])
    print(
        f"settled {len(matches)} players, graded {result['graded']} claims, "
        f"{result['missing_outcome']} had no outcome"
    )
    print(grading.report(summary) if summary else "  nothing graded yet")

    if dry_run:
        return 0

    # Results have just landed, which is exactly when the stats sheet changes.
    try:
        from foulgorithm.publish import matchday

        matchday.publish()
    except Exception as exc:
        print(f"stats sheet not refreshed: {exc}", file=sys.stderr)

    # Results land here: scores and the league's own team foul counts, which is
    # what the season timeline shows for a match that has been played.
    try:
        from foulgorithm.publish import season

        season.publish()
    except Exception as exc:
        print(f"season timeline not refreshed: {exc}", file=sys.stderr)

    # Points and positions move when results land.
    try:
        from foulgorithm.publish import teams

        teams.publish()
    except Exception as exc:
        print(f"league table not refreshed: {exc}", file=sys.stderr)

    # Played fixtures keep their pages; mark their picks with what happened.
    try:
        from foulgorithm.publish import archive

        archive.mark_all()
    except Exception as exc:
        print(f"fixture archive not marked: {exc}", file=sys.stderr)

    # The one question the lineup machinery exists to answer, asked of the
    # record after every matchday. See jobs/lineup_audit.py.
    try:
        from foulgorithm.jobs import lineup_audit

        line = lineup_audit.report(claims, sorted(settled))
        print(line, file=sys.stderr if "MISSING" in line else sys.stdout)
    except Exception as exc:  # noqa: BLE001 - an audit must never fail a settle
        print(f"lineup audit skipped: {exc}", file=sys.stderr)

    # The league table lives in players.json, which only a full publish
    # rewrote, so Saturday's grading did not reach The five until the next
    # lineups wake and Monday's round-closing grade waited until Friday.
    try:
        if refresh_table():
            print("league table refreshed")
    except Exception as exc:  # noqa: BLE001 - reported, never fatal to a settle
        print(f"league table not refreshed: {exc}", file=sys.stderr)

    # Results are selection pressure: magicIan breeds his next generation
    # from whatever the field's graded record now says works. See docs/38.
    try:
        from foulgorithm.models import evolve

        bred = evolve.step()
        print(
            f"magicIan generation {bred['generation']}: {bred['origin']} won "
            f"(fitness {bred['fitness']})"
        )
    except Exception as exc:
        print(f"magicIan did not evolve: {exc}", file=sys.stderr)

    TRACK_RECORD.parent.mkdir(parents=True, exist_ok=True)
    TRACK_RECORD.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(UTC).isoformat(),
                "settledPlayers": len(matches),
                "gradedClaims": result["graded"],
                "withoutOutcome": result["missing_outcome"],
                "models": summary,
            },
            indent=2,
        )
        + "\n"
    )
    taken_at = datetime.now(UTC).isoformat()
    kept = persist_matches(matches, previous.get("takenAt"), taken_at)
    if kept:
        print(f"kept {kept} per-match rows for training")

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"takenAt": taken_at, "totals": current}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(dry_run="--dry-run" in sys.argv))
