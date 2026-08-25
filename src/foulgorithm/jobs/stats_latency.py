"""Measure when the league's season totals actually move after a game.

Settle waits STATS_DELAY (3 hours) after every kickoff before trusting the
totals, and SETTLE_LAG (3h45) after a matchday's last kickoff before waking.
Both numbers are described in their own comments as comfortably conservative,
which means nobody has measured them. On a Saturday that caution is the
difference between grading at about 21:15 UK and grading not long after the
last whistle.

This is the instrument: started around a matchday, it takes a baseline of
`player_season_stats.season_totals()`, then polls every ten minutes and
appends one line per poll to `data/state/stats_latency.jsonl`, recording how
many players' totals have moved since the baseline and every fixture's
status at that moment. The waves in the moved-count, read against the
fixture statuses beside them, give each slot's posting latency, and show
whether the tables move IN-PLAY, which would mean no mid-afternoon snapshot
is ever safe regardless of delay.

Read-only by design: nothing here writes the settle snapshot or grades
anything. One weekend of evidence is the whole job; the workflow that runs
it (.github/workflows/latency.yml) should be deleted once the delays are
re-set from what this logs.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG = Path("data/state/stats_latency.jsonl")

POLL_SECONDS = 600
MAX_RUNTIME = timedelta(hours=5)

# Stop early once the day is over and the tables have been still this long:
# the question is answered and the remaining polls would measure nothing.
SETTLED_AFTER = timedelta(minutes=90)


def moved(baseline: dict, current: dict) -> dict:
    """How many players' totals rose since the baseline.

    `players` counts anyone with any stat higher (a debutant counts: absent
    from a ranked table means zero, not unknown). `appearances` counts only
    those whose appearance total rose, separately, because the stats are
    separate feeds and fouls have no reason to post in the same breath as
    appearances. Settle needs BOTH before a diff is attributable.
    """
    players = appearances = 0
    for name, stats in current.items():
        before = baseline.get(name) or {}
        if any(value > (before.get(stat) or 0.0) for stat, value in stats.items()):
            players += 1
            if (stats.get("appearances") or 0.0) > (before.get("appearances") or 0.0):
                appearances += 1
    return {"players": players, "appearances": appearances}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _todays_fixtures() -> list:
    from foulgorithm.sources import pulselive

    pulselive.forget()
    today = _now().date()
    return sorted(
        (f for f in pulselive.fixtures() if f.kickoff_utc.date() == today),
        key=lambda f: f.kickoff_utc,
    )


def run() -> int:
    """Poll the totals around today's games. 0 logged something, 1 no games."""
    from foulgorithm.sources import player_season_stats

    started = _now()
    fixtures = _todays_fixtures()
    if not fixtures:
        print("no fixtures today, nothing to measure")
        return 1

    print(f"measuring against {len(fixtures)} fixtures:")
    for f in fixtures:
        print(f"  {f.home} v {f.away}  kickoff {f.kickoff_utc:%H:%M}")

    baseline = player_season_stats.season_totals()
    print(f"baseline: {len(baseline)} players at {started:%H:%M}")

    last_change = started
    last_players = 0
    poll = 0
    while _now() - started < MAX_RUNTIME:
        time.sleep(POLL_SECONDS)
        poll += 1
        now = _now()
        try:
            current = player_season_stats.season_totals()
            fixtures = _todays_fixtures()
        except Exception as exc:  # noqa: BLE001 - one bad poll is a gap in the log, not the end of it
            print(f"  poll {poll} failed: {exc}", file=sys.stderr)
            continue

        held = moved(baseline, current)
        row = {
            "at": now.replace(microsecond=0).isoformat(),
            "poll": poll,
            **held,
            "fixtures": [
                {
                    "label": f"{f.home} v {f.away}",
                    "kickoff": f.kickoff_utc.isoformat(),
                    "status": f.status,
                }
                for f in fixtures
            ],
        }
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print(f"  {now:%H:%M} moved {held['players']} ({held['appearances']} with appearances)")

        if held["players"] != last_players:
            last_players = held["players"]
            last_change = now
        day_over = all(f.complete for f in fixtures)
        if day_over and now - last_change > SETTLED_AFTER:
            print("tables still and the day is over, done")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
