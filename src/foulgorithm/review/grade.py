"""Settle published predictions against what actually happened.

The other half of the honesty commitment. Publishing before kickoff is worth
nothing without this, and this is worth nothing unless it runs on everything,
including the predictions we would rather forget.

Outcomes come from the league's own API: it carries the result minutes after
full time and it is the same source the confirmed lineups come from.

Grading never edits a prediction. It writes a separate graded record, so the
original claim and the outcome are independently auditable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from foulgorithm.backtest import metrics as mx
from foulgorithm.store import predictions as pred_store

GRADED = Path("data/graded")


@dataclass(frozen=True)
class Graded:
    key: str
    entity: str
    market: str
    line: float
    probability: float
    model_id: str
    observed: float
    won: bool
    log_loss: float
    brier: float
    kickoff: str
    graded_at: str


def grade(
    outcomes: dict[tuple[str, str], float],
    predictions: list[dict] | None = None,
    root: Path = GRADED,
) -> dict:
    """Grade every prediction we have an outcome for.

    `outcomes` maps (entity, market) to the observed count. Anything without an
    outcome is left ungraded rather than guessed, and the count is reported so a
    silent gap cannot masquerade as a clean sheet.
    """
    rows = predictions if predictions is not None else pred_store.load_all()
    graded: list[Graded] = []
    missing = 0
    at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for row in rows:
        key = (row["entity"], row["market"])
        if key not in outcomes:
            missing += 1
            continue
        observed = float(outcomes[key])
        p = float(row["probability"])
        won = observed > row["line"]
        p_clamped = min(max(p, 1e-9), 1 - 1e-9)
        graded.append(
            Graded(
                key=row["key"],
                entity=row["entity"],
                market=row["market"],
                line=row["line"],
                probability=p,
                model_id=row["model_id"],
                observed=observed,
                won=won,
                log_loss=float(-np.log(p_clamped if won else 1 - p_clamped)),
                brier=float((p - (1.0 if won else 0.0)) ** 2),
                kickoff=row["kickoff"],
                graded_at=at,
            )
        )

    if graded:
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{graded[0].kickoff[:10]}.jsonl"
        seen = set()
        if path.exists():
            seen = {json.loads(l)["key"] for l in path.read_text().splitlines() if l.strip()}
        fresh = [g for g in graded if g.key not in seen]
        with path.open("a") as handle:
            for g in fresh:
                handle.write(json.dumps(g.__dict__) + "\n")

    return {
        "graded": len(graded),
        "missing_outcome": missing,
        "results": graded,
    }


def load_all(root: Path = GRADED) -> list[dict]:
    """Every graded claim on disk, oldest first."""
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarise(graded: list[Graded]) -> dict:
    """Per-model record, and the column that matters most.

    `claimed` against `actual` is the honest one. A table of hit rates alone
    would have hidden that the season replay found Alan overstating his own
    picks by 9.5 points while being well calibrated about the field.
    """
    by_model: dict[str, list[Graded]] = {}
    for g in graded:
        by_model.setdefault(g.model_id, []).append(g)

    out = {}
    for model, rows in by_model.items():
        claimed = float(np.mean([r.probability for r in rows]))
        actual = float(np.mean([1.0 if r.won else 0.0 for r in rows]))
        pairs = [(r.probability, r.won) for r in rows]
        out[model] = {
            "n": len(rows),
            "claimed": round(claimed, 4),
            "actual": round(actual, 4),
            "gap": round(actual - claimed, 4),
            "logLoss": round(float(np.mean([r.log_loss for r in rows])), 4),
            "brier": round(float(np.mean([r.brier for r in rows])), 4),
            "ece": round(mx.expected_calibration_error(pairs), 4),
            "calibration": mx.calibration_buckets(pairs),
        }
    return out


def report(summary: dict) -> str:
    lines = [
        f"{'model':<12}{'n':>7}{'claimed':>10}{'actual':>9}{'gap':>9}{'logloss':>10}{'ECE':>8}",
        "-" * 65,
    ]
    for model, s in sorted(summary.items(), key=lambda kv: kv[1]["logLoss"]):
        lines.append(
            f"{model:<12}{s['n']:>7}{s['claimed']:>10.1%}{s['actual']:>9.1%}"
            f"{s['gap']:>+9.1%}{s['logLoss']:>10.4f}{s['ece']:>8.4f}"
        )
    return "\n".join(lines)
