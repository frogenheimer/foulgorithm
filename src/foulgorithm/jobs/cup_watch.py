"""Poll for cup lineups and republish the cup slates.

The league watcher (lineup_watch_live.py) covers the league's own round. This
is kept SEPARATE on purpose so a cup problem can never take the league's
lineups down with it, and it stays separate now that both read the same source.

**Both cups run on the Premier League's own API.** It carries competition 4
(FA Cup) and 5 (EFL Cup) alongside its own, with `matchOfficials` naming the
referee and `teamLists` carrying the elevens in exactly the shape a league
fixture uses. So `sources.lineups.shape_detail` reads both and there is one
implementation rather than two that drift.

**The request-budget problem is gone rather than solved.** This job used to
poll API-Football per fixture every 90 seconds: about 47 requests for the one
hand-fed tie it was written for, and roughly 470 for a ten-tie round against a
free cap of 100 a day, which would have died mid-round and produced no elevens
at all. The league's API needs no key and meters no daily quota. Polling stays
gentle anyway, at three minutes, because the source is free and somebody else
pays to run it.

The wake times come from the same weekly reschedule as the league's
(jobs/schedule.py reads the cup slate too). The watch opens at T-70 because cup
elevens are no more punctual than the league's T-60, and gives up at kickoff.
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
POLL_SECONDS = 180
MAX_RUNTIME = timedelta(hours=3)
WITHIN = timedelta(hours=6)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def lineups_for(fixture_id: int, label: str, api=None) -> dict:
    """One tie's confirmed elevens, empty until the team sheets post.

    Empty is the ordinary answer until roughly an hour before kickoff, and it
    is not an error. A club outside our two divisions is skipped rather than
    raised on, because half a cup draw is clubs we hold nothing for.
    """
    from foulgorithm.sources import lineups as lineup_shapes
    from foulgorithm.sources import pulselive

    api = api or pulselive
    return lineup_shapes.shape_detail(api.fixture_detail(int(fixture_id)), label)


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
    from foulgorithm.sources import cup_slate
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

    # The slate comes FROM the fixture source, so every tie already carries its
    # id and the old per-tie lookup is gone.
    ids: dict[str, int] = {}
    for f in slate:
        label = f"{f['home_team_raw']} v {f['away_team_raw']}"
        ids[label] = f["fixture_id"]
        print(f"  {label}  {f['competition']}  kickoff {f['kickoff_utc']:%H:%M}  "
              f"fixture {f['fixture_id']}")

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
                lineups.update(lineups_for(ids[label], label))
            failures = 0
        except SourceError as exc:
            failures += 1
            backoff = min(POLL_SECONDS * (2 ** (failures - 1)), 600)
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
