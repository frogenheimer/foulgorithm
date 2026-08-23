"""Committed slates: which claims each character put on which fixed bet.

A slate is not a prediction. It is a SELECTION of predictions, and trying to
store it as one went wrong twice in a way worth recording.

Recording each leg as its own claim collides with the claim already there: same
player, same line, same model, same probability, so the same ledger key. The
dedupe skipped it, correctly, and the slate membership vanished with it.

Attaching membership to the claim's `extra` fails differently. The ledger is
append-only on purpose, so a claim recorded on Thursday cannot gain a field on
Friday, and every slate leg for an already-published claim was silently dropped.

Both failures are the append-only rule working as designed. The fix is to stop
arguing with it: a slate lives here, holding the KEYS of the claims it selected.
The claim stays untouched and says what we thought; the slate says what we
committed to. Grading joins them on the key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

STORE = Path("data/slates")


@dataclass(frozen=True)
class Committed:
    """One character's bet at one fixed shape, for one round."""

    published_at: str
    round: str                 # the Monday of the round, as an ISO date
    character: str
    slate: str
    claim_keys: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """One slate per character per shape per round."""
        return f"{self.round}|{self.character}|{self.slate}"

    def to_json(self) -> dict:
        return {"key": self.key, **self.__dict__}


def round_of(kickoff_iso: str) -> str:
    day = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00")).date()
    monday = day.fromordinal(day.toordinal() - day.weekday())
    return monday.isoformat()


def path_for(round_key: str, root: Path = STORE) -> Path:
    return root / f"{round_key}.jsonl"


def existing_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(line)["key"]
        for line in path.read_text().splitlines()
        if line.strip()
    }


def append(slates: list[Committed], root: Path = STORE) -> dict:
    """Write anything not already committed. Never rewrites a committed slate.

    A slate is a promise made before kickoff. Letting a later run replace it
    would make the table meaningless, so the first one recorded for a round
    stands.
    """
    if not slates:
        return {"written": 0, "skipped": 0, "files": []}

    by_file: dict[Path, list[Committed]] = {}
    for item in slates:
        by_file.setdefault(path_for(item.round, root), []).append(item)

    written = skipped = 0
    touched: list[str] = []
    for path, items in by_file.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        seen = existing_keys(path)
        fresh = []
        for item in items:
            if item.key in seen:
                skipped += 1
                continue
            seen.add(item.key)
            fresh.append(item)
        if not fresh:
            continue
        with path.open("a") as handle:
            for item in fresh:
                handle.write(json.dumps(item.to_json()) + "\n")
        written += len(fresh)
        touched.append(str(path))

    return {"written": written, "skipped": skipped, "files": touched}


def load_all(root: Path = STORE) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows
