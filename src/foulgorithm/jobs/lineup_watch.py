"""Poll for confirmed lineups and republish when they land.

**The site cannot do this itself, and that is deliberate.** It is a static
export with no backend, so there is no server for a button to call. Adding one
would mean either paying for serverless invocations or exposing a public
endpoint that anyone could use to hammer the Premier League's API on our behalf.
Neither is acceptable at a budget of zero.

So the poll runs in GitHub Actions instead, which is free on a public repo, and
writes its result into the repo. See .github/workflows/lineups.yml.

Confirmed lineups appear roughly an hour before kickoff. Until then this exits
having done nothing, which is the common case and must stay cheap.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from foulgorithm.sources.lineups import for_round as confirmed_lineups
from foulgorithm.store import positions as positions_store

# Committed, not cached. This lives outside data/raw/ because that directory is
# gitignored as reproducible cache, and this is a record of what the job has
# already seen. A scheduled run cannot commit an ignored path, so state kept
# there would be lost between every run.
STATE = Path("data/state/lineups_seen.json")


def fingerprint(lineups: dict) -> dict:
    """What we have seen, small enough to diff and commit."""
    return {
        key: {"formation": lu.formation, "starters": sorted(lu.starters)}
        for key, lu in sorted(lineups.items())
    }


def run(force: bool = False) -> int:
    """Republish if the confirmed lineups have changed. Returns an exit code.

    0 means something was published, 1 means nothing had changed. The caller
    uses that to decide whether to commit, so an unchanged round costs nothing.
    """
    try:
        lineups = confirmed_lineups()
    except Exception as exc:
        # A dead source must be loud. Silently publishing predicted elevens
        # while labelling them confirmed would be the worst possible failure.
        print(f"lineup source failed: {exc}", file=sys.stderr)
        return 2
    # Every confirmed sheet teaches the next predicted pitch where people
    # actually play. See store/positions.py.
    positions_store.remember(lineups)

    current = fingerprint(lineups)
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}

    if not force and current == previous.get("lineups"):
        print(f"no change, {len(current)} confirmed")
        return 1

    from foulgorithm.publish import matchday, player_round

    result = player_round.publish()
    # The stats sheet moves when results land, not when lineups do, but it is
    # cheap and republishing both together keeps the two pages from disagreeing
    # about which round it is.
    try:
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
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {"checkedAt": datetime.now(UTC).isoformat(), "lineups": current},
            indent=2,
        )
        + "\n"
    )
    confirmed = result.get("lineups", {}).get("confirmed", 0)
    print(f"published, {confirmed} confirmed lineups, {len(result.get('picks', []))} characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(force="--force" in sys.argv))
