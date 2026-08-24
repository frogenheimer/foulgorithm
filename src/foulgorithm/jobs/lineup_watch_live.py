"""Poll for confirmed lineups on a tight loop, inside one job.

**Why not cron.** The Premier League publishes confirmed elevens at T-60. A cron
every 30 minutes catches that somewhere between T-60 and T-30, and GitHub's
scheduler is documented as running late under load, sometimes by 15 minutes or
more. Stacking those, a fixture could be published at T-15 or missed entirely.
Tightening the cron does not fix it: the jitter is in the scheduler, not the
interval.

So the scheduler only has to start this job roughly on time. Everything precise
happens inside it: work out when the next lineups are due, wait, then poll every
minute until they land. One run covers a whole afternoon of fixtures.

A pick published before lineups and one published after are different products
with different accuracy, graded separately, and it is the second one this exists
to deliver on time.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone

# Lineups land at T-60, and in practice exactly T-60: Oliver's observation,
# 2026-08-24, is that they are never early. So the watch opens at T-65, a
# small buffer for a clock being what it is, rather than the old T-75, which
# spent ten polls a fixture asking a question whose answer was known.
LOOK_FROM = timedelta(minutes=65)
# Give up on a fixture at kickoff: a lineup that has not appeared by then is
# not going to be useful, and the match is under way.
GIVE_UP_AT = timedelta(minutes=0)
POLL_SECONDS = 60
MAX_RUNTIME = timedelta(hours=5, minutes=30)

# A failed poll backs off and keeps going, up to this long between attempts.
# One transient API failure used to end the whole afternoon's watch, which
# for a job whose entire purpose is being present at T-60 is the worst
# possible response to a hiccup.
MAX_BACKOFF_SECONDS = 300

# The fixture list at startup gets this many attempts before the run declares
# the source dead. Thirty seconds apart: a real outage fails all of them, a
# blip fails one.
STARTUP_ATTEMPTS = 3
STARTUP_RETRY_SECONDS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upcoming(within: timedelta = timedelta(hours=6)) -> list:
    from foulgorithm.sources import pulselive

    # The fixture list is cached for the process, which saves a publish run
    # ninety seconds and would quietly break this one. This job runs for five
    # and a half hours and exists to notice kickoff moves and referee
    # appointments, so it re-asks every round.
    pulselive.forget()

    now = _now()
    return sorted(
        (
            f
            for f in pulselive.fixtures()
            if f.status == pulselive.STATUS_UPCOMING
            and now - timedelta(minutes=10) <= f.kickoff_utc <= now + within
        ),
        key=lambda f: f.kickoff_utc,
    )


def run(poll_seconds: int = POLL_SECONDS, once: bool = False) -> int:
    """Watch until every fixture in the window has a lineup, or kickoff passes.

    Returns 0 if anything was published, 1 if there was nothing to wait for,
    2 if the source failed.
    """
    from foulgorithm.jobs import lineup_watch

    started = _now()

    # The fixture call is being made anyway, so notice if the round itself has
    # moved: kickoff times shift for television and referees are appointed late.
    try:
        from foulgorithm.jobs import changes

        for c in changes.run(quiet=True):
            print(f"  round changed: {c['fixture']} {c['change']}")
    except Exception as exc:
        print(f"change check skipped: {exc}", file=sys.stderr)

    fixtures = None
    for attempt in range(STARTUP_ATTEMPTS):
        try:
            fixtures = upcoming()
            break
        except Exception as exc:  # noqa: BLE001 - retried, then loud
            print(
                f"fixture list unavailable (attempt {attempt + 1} of "
                f"{STARTUP_ATTEMPTS}): {exc}",
                file=sys.stderr,
            )
            if attempt + 1 < STARTUP_ATTEMPTS:
                time.sleep(STARTUP_RETRY_SECONDS)
    if fixtures is None:
        return 2

    if not fixtures:
        print("no fixtures kicking off in the next six hours")
        return 1

    print(f"watching {len(fixtures)} fixtures:")
    for f in fixtures:
        due = f.kickoff_utc - LOOK_FROM
        print(f"  {f.home} v {f.away}  kickoff {f.kickoff_utc:%H:%M}  watching from {due:%H:%M}")

    published = False
    failures = 0
    lost_during_outage = False
    outstanding = {f"{f.home}|{f.away}": f for f in fixtures}

    while outstanding and _now() - started < MAX_RUNTIME:
        now = _now()

        # Drop anything already under way. Nothing useful arrives after kickoff.
        for key, f in list(outstanding.items()):
            if now >= f.kickoff_utc + GIVE_UP_AT:
                print(f"  {f.home} v {f.away}: kicked off without a lineup we could use")
                lost_during_outage = lost_during_outage or failures > 0
                del outstanding[key]
        if not outstanding:
            break

        watching = [f for f in outstanding.values() if now >= f.kickoff_utc - LOOK_FROM]
        if not watching:
            # Sleep until the earliest fixture enters its window, rather than
            # burning a poll a minute for two hours.
            soonest = min(f.kickoff_utc - LOOK_FROM for f in outstanding.values())
            wait = max((soonest - now).total_seconds(), 0) + 1
            print(f"  nothing due yet, sleeping {wait / 60:.0f} min until {soonest:%H:%M}")
            if once:
                return 1
            time.sleep(min(wait, MAX_RUNTIME.total_seconds()))
            continue

        # A failed poll is a failed POLL, never a failed afternoon. The job's
        # entire purpose is being present when the team sheets land, so a
        # transient source error or a publish crash backs off and tries
        # again while any fixture is still ahead of kickoff. Giving up is
        # reserved for the window actually ending.
        try:
            code = lineup_watch.run()
        except Exception as exc:  # noqa: BLE001 - a crash mid-publish must not end the watch
            print(f"  poll crashed, retrying: {exc}", file=sys.stderr)
            code = 2

        if code == 0:
            published = True
            failures = 0
            print(f"  {_now():%H:%M} published")
            # Which of the ones we are waiting on now have a team list.
            for key, f in list(outstanding.items()):
                if _has_lineup(f):
                    print(f"  {f.home} v {f.away}: lineup in, {(f.kickoff_utc - _now()).total_seconds() / 60:.0f} min before kickoff")
                    del outstanding[key]
        elif code == 2:
            failures += 1
            backoff = min(poll_seconds * (2 ** (failures - 1)), MAX_BACKOFF_SECONDS)
            print(
                f"  source failed, {failures} in a row, retrying in {backoff:.0f}s",
                file=sys.stderr,
            )
            if once:
                break
            time.sleep(backoff)
            continue
        else:
            failures = 0

        if once:
            break
        time.sleep(poll_seconds)

    if lost_during_outage and not published:
        # A fixture kicked off unpublished while the source was down. That is
        # the one outcome that must read as a failure rather than a quiet
        # afternoon, because it is the exact event this job exists to prevent.
        return 2
    return 0 if published else 1


def _has_lineup(fixture) -> bool:
    from foulgorithm.sources import pulselive

    try:
        raw = pulselive._get(f"fixtures/{fixture.id}")
        lists = raw.get("teamLists") or []
        return bool(lists and (lists[0] or {}).get("lineup"))
    except Exception:
        return False


if __name__ == "__main__":
    raise SystemExit(run(once="--once" in sys.argv))
