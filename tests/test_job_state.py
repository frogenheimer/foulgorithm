"""Scheduled jobs keep state between runs, and that state has to survive.

Both job state files originally lived under `data/raw/`, which is gitignored as
a reproducible cache. It is not one. These files are the record of what a job
has already seen, and losing them changes what the next run does.

For the lineup poller that means republishing every time, which is wasteful.
For settlement it is much worse: with no previous snapshot, a player's whole
SEASON total gets treated as one match's outcome, and claims are graded against
numbers that never happened. That is precisely the fake-track-record failure
the settlement tests exist to prevent, reintroduced through a gitignore rule
rather than through code.

The workflow would have failed loudly rather than silently, because git refuses
to add an ignored path. It would still have failed every single run.
"""

import subprocess
from pathlib import Path

import pytest

from foulgorithm.jobs import lineup_watch, settle

STATE_PATHS = [
    lineup_watch.STATE,
    settle.SNAPSHOT,
]


def _ignored(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=Path(__file__).resolve().parent.parent,
        ).returncode
        == 0
    )


@pytest.mark.parametrize("path", STATE_PATHS, ids=lambda p: str(p))
def test_job_state_is_committable(path: Path):
    assert not _ignored(path), (
        f"{path} is gitignored, so the scheduled job cannot commit it and every "
        "run starts from nothing. Job state is a record, not a cache."
    )


@pytest.mark.parametrize("path", STATE_PATHS, ids=lambda p: str(p))
def test_job_state_lives_outside_the_raw_cache(path: Path):
    # A path under data/raw/ would be ignored today and re-ignored by anyone
    # tidying the gitignore later. Keeping state out of the cache directory
    # makes the rule obvious rather than a coincidence.
    assert "raw" not in path.parts, f"{path} sits in the raw cache directory"


def test_the_workflows_commit_the_paths_the_jobs_write():
    """A workflow adding a path no job writes, or missing one it does, is dead."""
    root = Path(__file__).resolve().parent.parent
    for name, expected in (
        ("lineups.yml", lineup_watch.STATE),
        ("settle.yml", settle.SNAPSHOT),
    ):
        text = (root / ".github" / "workflows" / name).read_text()
        assert str(expected) in text, f"{name} does not commit {expected}"
