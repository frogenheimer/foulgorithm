"""Notice when the round itself moves, not just when lineups land.

The fixture call the lineup watcher already makes carries kickoff time, referee
and status. Comparing it against what we last saw costs nothing and catches
three things that would otherwise pass silently:

  - **Kickoff times move.** Matches are rescheduled for television, and the
    league's default before that happens is to list a whole round at the same
    time. A fixture that shifts after the cron was generated is a fixture whose
    lineup we would miss entirely.
  - **Referees are appointed late.** Every upcoming fixture reports no referee
    and gains one a few days out.
  - **Fixtures get postponed.**

Written as a record rather than an alert. A round that quietly changed shape
under a published prediction is the kind of thing that should be findable
afterwards.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

STATE = Path("data/state/fixture_state.json")


def snapshot(fixtures) -> dict:
    return {
        str(f.id): {
            "fixture": f"{f.home} v {f.away}",
            "kickoff": f.kickoff_utc.isoformat(),
            "referee": f.referee,
            "status": f.status,
        }
        for f in fixtures
    }


def diff(before: dict, after: dict) -> list[dict]:
    """What moved. Additions count; removals are reported as gone rather than dropped."""
    out = []
    for fid, now in after.items():
        was = before.get(fid)
        if was is None:
            out.append({"fixture": now["fixture"], "change": "added", "to": now["kickoff"]})
            continue
        if was["kickoff"] != now["kickoff"]:
            out.append(
                {
                    "fixture": now["fixture"],
                    "change": "kickoff moved",
                    "from": was["kickoff"],
                    "to": now["kickoff"],
                }
            )
        if was["referee"] != now["referee"]:
            out.append(
                {
                    "fixture": now["fixture"],
                    "change": "referee" if was["referee"] else "referee appointed",
                    "from": was["referee"],
                    "to": now["referee"],
                }
            )
        if was["status"] != now["status"]:
            out.append(
                {
                    "fixture": now["fixture"],
                    "change": "status",
                    "from": was["status"],
                    "to": now["status"],
                }
            )
    for fid, was in before.items():
        if fid not in after:
            out.append({"fixture": was["fixture"], "change": "gone from the list"})
    return out


def run(quiet: bool = False) -> list[dict]:
    """Compare the current fixture list against the last one seen."""
    from foulgorithm.sources import pulselive

    try:
        current = snapshot(pulselive.fixtures())
    except Exception as exc:
        print(f"fixture list unavailable: {exc}", file=sys.stderr)
        return []
    if not current:
        return []

    previous = json.loads(STATE.read_text()).get("fixtures", {}) if STATE.exists() else {}
    changes = diff(previous, current)

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {
                "checkedAt": datetime.now(UTC).isoformat(),
                "fixtures": current,
                "lastChanges": changes,
            },
            indent=2,
        )
        + "\n"
    )

    if changes and not quiet:
        print(f"{len(changes)} change(s) to the round:")
        for c in changes[:20]:
            detail = f" {c.get('from')} -> {c.get('to')}" if "to" in c else ""
            print(f"  {c['fixture']}: {c['change']}{detail}")
    elif not quiet:
        print(f"no change, {len(current)} fixtures tracked")
    return changes


if __name__ == "__main__":
    run()
