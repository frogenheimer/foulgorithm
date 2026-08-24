"""Backfill the fixture archive from git history.

The archive (publish/archive.py) only started existing today, but every
payload the site ever served is in git, one commit per publish. This walks
the history of site/public/data/players.json oldest first, feeds each
snapshot through the same write_round used live (so the pre-kickoff binding
rule applies identically), pairs it with the matchday sheet from the same
commit, and finally marks outcomes from the graded stores.

Idempotent: re-running replays the same history into the same files. Run
from the repository root:

    PYTHONPATH=src .venv/bin/python scripts/backfill_fixture_archive.py
"""

import json
import subprocess
import sys

from foulgorithm.publish import archive


def git_show(sha: str, path: str) -> dict | None:
    proc = subprocess.run(
        ["git", "show", f"{sha}:{path}"], capture_output=True, text=True
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    shas = subprocess.run(
        ["git", "log", "--reverse", "--format=%H", "--", "site/public/data/players.json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    print(f"{len(shas)} payload snapshots in history")
    written_total = 0
    for sha in shas:
        payload = git_show(sha, "site/public/data/players.json")
        if not payload or not payload.get("fixtureSlips"):
            continue
        matchday = git_show(sha, "site/public/data/matchday.json")
        written = archive.write_round(payload, matchday=matchday)
        if written:
            print(f"  {sha[:9]} {payload.get('generatedAt', '?'):<26} wrote {written}")
            written_total += written

    marked = archive.mark_all()
    print(f"backfill done: {written_total} writes, {marked} fixtures marked with outcomes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
