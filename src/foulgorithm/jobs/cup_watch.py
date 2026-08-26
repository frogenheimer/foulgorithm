"""Poll for cup lineups from API-Football and republish the cup slate.

The league watcher (lineup_watch_live.py) cannot do this: its source is the
Premier League API, which does not know cup games exist. This is the same
watch pattern against the source that does, kept SEPARATE on purpose so a
cup problem can never take the league's own lineups down with it.

Scope now matches publish/cups.py: every tie in either domestic cup where we
hold match history for both clubs, which means Premier League and Championship.
The wake times come from the same weekly reschedule as the league's
(jobs/schedule.py reads the cup slate too); the watch opens at T-70 because
API-Football posts cup elevens less punctually than the league's T-60, and
gives up at kickoff.

**The request budget is the binding constraint, and it changed.** The free plan
meters 100 requests a day, reset at midnight UTC with no rollover. This job used
to poll per fixture every 90 seconds, which cost about 47 requests for the one
hand-fed tie it was written for. An FA Cup third round can leave ten qualifying
ties on one afternoon, and ten fixtures at that cadence is 470 requests: the
watch would die four fifths of the way through and we would get no elevens at
all, which is worse than getting them for one tie.

So one request now covers every tie in the window rather than one each
(`fixtures?ids=` takes up to 20), and the cadence is five minutes rather than
90 seconds. Cup elevens land 40 to 70 minutes out and nobody is betting these
pages, so five-minute granularity costs nothing. A full 22-tie slate now costs
about 14 requests for the whole watch.
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
POLL_SECONDS = 300
MAX_RUNTIME = timedelta(hours=3)
WITHIN = timedelta(hours=6)

#: API-Football's free plan, per docs/02-data-sources. Reset at 00:00 UTC,
#: no rollover, and the whole project's only metered source.
DAILY_CAP = 100

#: Most ids `fixtures?ids=` accepts in one request.
BATCH = 20


def batches(ids: list) -> list[list]:
    """Fixture ids grouped into single requests."""
    return [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]


def requests_per_cycle(ties: int) -> int:
    """Requests one poll costs. One per batch, not one per tie."""
    return -(-ties // BATCH)


def watch_cost(ties: int, look_from: timedelta = LOOK_FROM,
               poll_seconds: int = POLL_SECONDS) -> int:
    """Requests a full watch spends, for the budget tests to hold us to."""
    cycles = int(look_from.total_seconds() // poll_seconds) + 1
    return requests_per_cycle(ties) * cycles


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
    from foulgorithm.publish import cups
    from foulgorithm.sources import api_football, cup_slate
    from foulgorithm.sources.base import SourceError

    started = _now()
    try:
        slate = [
            f for f in cup_slate.fetch(now=started)
            if f["kickoff_utc"] <= started + WITHIN
        ]
    except SourceError as exc:
        print(f"cup slate unreadable: {exc}", file=sys.stderr)
        return 2
    if not slate:
        print("no cup fixtures kicking off in the next six hours")
        return 1

    # The slate now comes FROM API-Football, so every tie already carries its
    # fixture id and the old per-tie lookup is gone. That is two fewer requests
    # a tie before the watch even starts.
    ids: dict[str, int] = {}
    for f in slate:
        label = f"{f['home_team_raw']} v {f['away_team_raw']}"
        ids[label] = f["fixture_id"]
        print(f"  {label}  {f['competition']}  kickoff {f['kickoff_utc']:%H:%M}  "
              f"api-football {f['fixture_id']}")
    print(f"  budget: about {watch_cost(len(slate))} requests for this watch, "
          f"cap is {DAILY_CAP} a day")

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
            # One request per batch of twenty, never one per tie. See the
            # module docstring: per-tie polling put a ten-tie round at 470
            # requests against a cap of 100.
            by_id = {ids[label]: label for label in watching}
            for batch in batches(list(by_id)):
                lineups.update(api_football.cup_lineups_batch(batch, by_id))
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
            cups.publish(lineups=lineups)
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
