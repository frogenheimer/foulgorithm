"""Poll for cup lineups from API-Football and republish the cup slate.

The league watcher (lineup_watch_live.py) cannot do this: its source is the
Premier League API, which does not know cup games exist. This is the same
watch pattern against the source that does, kept SEPARATE on purpose so a
cup problem can never take the league's own lineups down with it.

Beta scope, matching publish/cup.py: hand-fed ties between two of our
twenty clubs, in the two domestic cups. The wake times come from the same
weekly reschedule as the league's (jobs/schedule.py reads the cup slate
too); the watch opens at T-70 because API-Football posts cup elevens less
punctually than the league's T-60, and gives up at kickoff.

Requires `API_FOOTBALL_KEY`. Polling is deliberately gentle at 90 seconds:
the free plan meters requests per day, and a whole watch costs about
fifty of them.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Committed, not cached, like lineup_watch.STATE and for the same reason: it
# is the record of what the job has already seen and published.
STATE = Path("data/state/cup_lineups_seen.json")

LOOK_FROM = timedelta(minutes=70)
POLL_SECONDS = 90
MAX_RUNTIME = timedelta(hours=3)
WITHIN = timedelta(hours=6)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fingerprint(lineups: dict) -> dict:
    return {
        key: {"formation": lu.formation, "starters": sorted(lu.starters)}
        for key, lu in sorted(lineups.items())
    }


def run(once: bool = False) -> int:
    """Watch the cup slate until its elevens land, or kickoff passes.

    Returns 0 if anything was published, 1 if there was nothing to wait
    for, 2 if the source failed while a fixture was still waiting.
    """
    from foulgorithm.publish import cup
    from foulgorithm.sources import api_football
    from foulgorithm.sources.base import SourceError

    started = _now()
    try:
        slate = [
            f for f in cup.load_fixtures() if f["kickoff_utc"] <= started + WITHIN
        ]
    except SourceError as exc:
        print(f"cup slate unreadable: {exc}", file=sys.stderr)
        return 2
    if not slate:
        print("no cup fixtures kicking off in the next six hours")
        return 1

    # The tie's API-Football id, found once per fixture. A tie the API cannot
    # match is loud, not skipped: the slate was written by hand to be watched.
    ids: dict[str, int] = {}
    for f in slate:
        label = f"{f['home_team_raw']} v {f['away_team_raw']}"
        try:
            fixture_id = api_football.cup_fixture_id(
                f["home_team_raw"], f["away_team_raw"], f["kickoff_utc"]
            )
        except SourceError as exc:
            print(f"cup fixture lookup failed: {exc}", file=sys.stderr)
            return 2
        if fixture_id is None:
            print(f"  {label}: no cup lists this tie on API-Football", file=sys.stderr)
            return 2
        ids[label] = fixture_id
        print(f"  {label}  kickoff {f['kickoff_utc']:%H:%M}  api-football {fixture_id}")

    published = False
    outstanding = {f"{f['home_team_raw']} v {f['away_team_raw']}": f for f in slate}
    failures = 0

    while outstanding and _now() - started < MAX_RUNTIME:
        now = _now()
        for label, f in list(outstanding.items()):
            if now >= f["kickoff_utc"]:
                print(f"  {label}: kicked off without a lineup we could use")
                del outstanding[label]
        if not outstanding:
            break

        watching = [
            label
            for label, f in outstanding.items()
            if now >= f["kickoff_utc"] - LOOK_FROM
        ]
        if not watching:
            soonest = min(f["kickoff_utc"] - LOOK_FROM for f in outstanding.values())
            wait = max((soonest - now).total_seconds(), 0) + 1
            print(f"  nothing due yet, sleeping {wait / 60:.0f} min until {soonest:%H:%M}")
            if once:
                return 1
            time.sleep(min(wait, MAX_RUNTIME.total_seconds()))
            continue

        lineups: dict = {}
        try:
            for label in watching:
                lineups.update(api_football.cup_lineups(ids[label], label))
            failures = 0
        except SourceError as exc:
            failures += 1
            backoff = min(POLL_SECONDS * (2 ** (failures - 1)), 300)
            print(f"  source failed, {failures} in a row, retrying in {backoff:.0f}s", file=sys.stderr)
            if once:
                return 2
            time.sleep(backoff)
            continue

        current = fingerprint(lineups)
        previous = json.loads(STATE.read_text()) if STATE.exists() else {}
        if lineups and current != previous:
            from foulgorithm.store import positions as positions_store

            # A real team sheet teaches the predicted pitches too.
            positions_store.remember(lineups)
            cup.publish_cup(lineups=lineups)
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps(current, indent=2, sort_keys=True))
            published = True
            print(f"  {_now():%H:%M} published with {len(lineups)} confirmed sheets")
            for label in list(outstanding):
                if any(key.endswith(f"|{label}") for key in lineups):
                    del outstanding[label]

        if once:
            break
        time.sleep(POLL_SECONDS)

    return 0 if published else 1


if __name__ == "__main__":
    raise SystemExit(run(once="--once" in sys.argv))
