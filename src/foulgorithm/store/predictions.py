"""Append-only store for published predictions.

Predictions currently live in a JSON file the publisher overwrites, so every
run destroys the last one. The site presents itself as something that publishes
before kickoff and grades afterwards, and neither half can be true while the
record is being deleted on a schedule.

Design, and the reasons for it:

  - **Append-only.** A prediction is a claim made at a moment. It is never
    edited and never deleted, which is the project's stated honesty commitment
    and the only thing that makes a track record worth reading.
  - **One file per round**, newline-delimited JSON, committed to git. Git gives
    us timestamps we did not write ourselves, which is a far stronger claim to
    "published before kickoff" than a field in our own database.
  - **Idempotent.** Re-running a publish for the same round replaces nothing;
    a prediction already recorded is skipped, so a cron firing twice is safe.
    That check covers the batch as well as the file. It once covered only the
    file, so a run emitting the same player twice wrote him twice: both copies
    were absent when the check ran. Grading joins on the claim, so a repeat is
    a double-counted bet.

Deliberately not a database. The volume is a few hundred rows a week and the
value is in the audit trail, which a file in version control provides better
than Postgres does.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

STORE = Path("data/predictions")


@dataclass(frozen=True)
class Prediction:
    """One published claim. The natural key is everything that identifies it."""

    published_at: str
    kickoff: str
    fixture: str
    entity: str            # player name, or the fixture for match markets
    market: str
    line: float
    probability: float
    model_id: str
    model_version: str
    lineup_confirmed: bool
    thin: bool
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Stable identity, so the same claim is never stored twice."""
        raw = "|".join(
            [
                self.fixture, self.entity, self.market, f"{self.line}",
                self.model_id, self.model_version, str(self.lineup_confirmed),
            ]
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_json(self) -> dict:
        return {"key": self.key, **{k: v for k, v in self.__dict__.items()}}


def round_path(kickoff_iso: str, root: Path = STORE) -> Path:
    """One file per round, named for the week its first fixture falls in."""
    day = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00")).date()
    monday = day.fromordinal(day.toordinal() - day.weekday())
    return root / f"{monday.isoformat()}.jsonl"


def existing_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text().splitlines():
        if line.strip():
            keys.add(json.loads(line)["key"])
    return keys


def append(predictions: list[Prediction], root: Path = STORE) -> dict:
    """Write anything not already recorded. Never rewrites, never deletes."""
    if not predictions:
        return {"written": 0, "skipped": 0, "files": []}

    by_file: dict[Path, list[Prediction]] = {}
    for p in predictions:
        by_file.setdefault(round_path(p.kickoff, root), []).append(p)

    written = skipped = 0
    touched = []
    for path, items in by_file.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        seen = existing_keys(path)
        fresh = []
        for p in items:
            if p.key in seen:
                skipped += 1
                continue
            seen.add(p.key)   # so a repeat later in this batch is caught too
            fresh.append(p)
        if not fresh:
            continue
        with path.open("a") as handle:
            for p in fresh:
                handle.write(json.dumps(p.to_json()) + "\n")
        written += len(fresh)
        touched.append(str(path))

    return {"written": written, "skipped": skipped, "files": touched}


def load_all(root: Path = STORE) -> list[dict]:
    """Every prediction ever published, oldest first."""
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
