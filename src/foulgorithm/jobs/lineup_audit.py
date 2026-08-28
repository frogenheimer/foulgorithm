"""Did a confirmed eleven reach the record before kickoff?

The lineup component has one job: a version of every bet built from the
confirmed elevens, published before the game starts. Everything else about
it (crons, watchers, feeds) is machinery, and machinery drifts. This asks
the only question that matters, from the append-only record itself, and
settle prints the answer after every matchday so a miss is loud within
hours rather than discovered weeks later in the track record.
"""

from __future__ import annotations


def coverage(predictions: list[dict], fixtures: list[str]) -> dict[str, str | None]:
    """fixture -> published_at of its earliest confirmed-eleven claim before
    kickoff, or None when no such claim exists."""
    out: dict[str, str | None] = {f: None for f in fixtures}
    for row in predictions:
        fixture = row.get("fixture")
        if fixture not in out or not row.get("lineup_confirmed"):
            continue
        published = str(row.get("published_at") or "")
        kickoff = str(row.get("kickoff") or "")
        if not published or not kickoff or published >= kickoff:
            continue
        if out[fixture] is None or published < out[fixture]:
            out[fixture] = published
    return out


def report(predictions: list[dict], fixtures: list[str]) -> str:
    held = coverage(predictions, fixtures)
    covered = sum(1 for v in held.values() if v)
    misses = [f for f, v in held.items() if not v]
    line = f"confirmed elevens before kickoff: {covered} of {len(fixtures)}"
    if misses:
        line += " | MISSING: " + ", ".join(misses)
    return line
