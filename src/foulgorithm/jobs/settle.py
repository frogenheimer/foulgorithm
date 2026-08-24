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
from datetime import datetime, timezone
from pathlib import Path

# Committed, not cached. See lineup_watch.STATE for why. It matters more here:
# with no previous snapshot, per_match() diffs against nothing and a player's
# whole SEASON total is graded as one match's outcome.
SNAPSHOT = Path("data/state/player_season_totals.json")
TRACK_RECORD = Path("site/public/data/track-record.json")

MARKETS = {"fouls": "player_fouls_committed", "was_fouled": "player_fouls_drawn"}


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
            now.get(k, 0) < was.get(k, 0) for k in ("fouls", "was_fouled")
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
        }
    return out


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


def pending_fixtures(fixtures, now=None) -> list:
    """Fixtures that have started but whose stats may not have posted yet.

    A player's fouls are the difference between two snapshots, so a snapshot
    taken while a match is half-posted does its damage later, not now: it
    becomes the next run's baseline, the fouls arrive in a window where
    appearances did not move, and the exactly-one-appearance rule discards
    them permanently. Three fixtures graded near zero this way on 22 August,
    all from the same 14:00 slot.

    `STATS_DELAY` is shared with the history loader, which already calls three
    hours conservative for the same publishing lag.
    """
    from foulgorithm.store.players import STATS_DELAY

    now = now or datetime.now(timezone.utc)
    return [
        f
        for f in fixtures
        if f.kickoff_utc <= now and (now - f.kickoff_utc) < STATS_DELAY
    ]


def _settled_fixtures() -> set[str]:
    """Fixtures that have finished, named the way predictions record them."""
    from foulgorithm.identity.teams import from_pulselive
    from foulgorithm.sources import pulselive

    return {
        f"{from_pulselive(f.home)} v {from_pulselive(f.away)}"
        for f in pulselive.fixtures()
        if f.complete
    }


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
    settled = _settled_fixtures()
    if not settled:
        print("no completed fixtures to settle against")
        return 1
    claims = [r for r in pred_store.load_all() if r["fixture"] in settled]
    if not claims:
        print(f"{len(settled)} fixtures settled, but no predictions match them")
        return 1

    result = grading.grade(outcomes(matches), predictions=claims)
    summary = grading.summarise(result["results"])
    print(f"settled {len(matches)} players, graded {result['graded']} claims, "
          f"{result['missing_outcome']} had no outcome")
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

    TRACK_RECORD.parent.mkdir(parents=True, exist_ok=True)
    TRACK_RECORD.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "settledPlayers": len(matches),
                "gradedClaims": result["graded"],
                "withoutOutcome": result["missing_outcome"],
                "models": summary,
            },
            indent=2,
        )
        + "\n"
    )
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(
        json.dumps(
            {"takenAt": datetime.now(timezone.utc).isoformat(), "totals": current},
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(dry_run="--dry-run" in sys.argv))
