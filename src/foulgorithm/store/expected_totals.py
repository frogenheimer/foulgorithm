"""What we said each fixture would produce, kept after it is played.

"We said 22" beside "Fouls 10-13" is the honesty proposition in one line, and it
was read off the current board. The board only holds what we are predicting now,
so the moment the pipeline moved to predicting the round that is COMING, every
played fixture lost its claim and the comparison disappeared without anything
failing.

A claim made before kickoff outlives the round it was made in. Recorded once,
never revised: a number that can be edited after the result is known is not a
prediction.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

STORE = Path("data/state")
FILE = "expected_totals.json"


def _path(root: Path = STORE) -> Path:
    return root / FILE


def load(root: Path = STORE) -> dict:
    path = _path(root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def record(totals: dict[str, float], published_at: str, root: Path = STORE) -> int:
    """Keep any fixture we have not already made a claim about.

    Returns how many were new. A zero total means the board had nobody in it
    rather than that we expect a quiet match, so it is not a claim.
    """
    fresh = {label: total for label, total in (totals or {}).items() if total and total > 0}
    if not fresh:
        return 0

    held = load(root)
    added = 0
    for label, total in fresh.items():
        if label in held:
            continue
        held[label] = {
            "expected": round(float(total), 1),
            "publishedAt": published_at or datetime.now(UTC).isoformat(),
        }
        added += 1

    if added:
        path = _path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(held, indent=1, sort_keys=True))
    return added
