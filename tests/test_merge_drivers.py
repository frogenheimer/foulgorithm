"""Parallel job runs must merge, never conflict.

On 29 August 2026 two lineups runs raced by seconds: the second published the
15:00 elevens and lost them to a rebase conflict. The append-only stores
merge as a union of lines; regenerated payloads and job state keep the side
being rebased; every workflow that commits enables the ours driver."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTRS = (ROOT / ".gitattributes").read_text()


def test_append_only_stores_merge_as_a_union():
    for pattern in ("data/predictions/*.jsonl", "data/slates/*.jsonl", "data/graded/*.jsonl"):
        assert f"{pattern} merge=union" in ATTRS, pattern


def test_regenerated_payloads_keep_their_own_side():
    for pattern in (
        "site/public/data/*.json",
        "site/public/data/fixtures/*.json",
        "data/state/*.json",
    ):
        assert f"{pattern} merge=ours" in ATTRS, pattern


def test_every_committing_workflow_enables_the_ours_driver():
    for name in ("lineups.yml", "settle.yml", "reschedule.yml", "latency.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text()
        if "git commit" in text:
            assert "git config merge.ours.driver true" in text, name
