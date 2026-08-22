"""Walk-forward evaluation for player markets.

The match-total bake-off has existed since day one. The player models shipped
without one, which meant the five characters were being compared on my
impression of their output. This closes that.

Protocol, per matchweek in the evaluation window:
  1. as_of is the earliest kickoff that week
  2. models refit on rows with known_at <= as_of, and nothing else
  3. predict every player who actually featured that week
  4. score, advance

Predicting only players who featured is a deliberate simplification. It removes
the selection question, which is a separate model, so this measures the FOUL
model alone rather than the two tangled together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.models import player_models as pm

LINES = (0.5, 1.5, 2.5)


@dataclass
class PlayerResult:
    character: str
    market: str
    n: int
    mae: float
    log_loss: float
    log_loss_by_line: dict[float, float]
    ece: float
    calibration: list[dict] = field(default_factory=list)


def walk_forward(
    history: pd.DataFrame,
    market: str = "player_fouls_committed",
    start: str = "2023-01-01",
    min_train: int = 20000,
    lines: tuple[float, ...] = LINES,
    characters: list[str] | None = None,
) -> list[PlayerResult]:
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    evaluation = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    if evaluation.empty:
        raise ValueError(f"no player-matches at or after {start}")

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"

    results = []
    for cid in characters or list(pm.CHARACTER_SETTINGS):
        model = pm.build(cid, market)
        errors: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
            train = history[history["known_at"] <= as_of]
            if len(train) < min_train:
                continue
            model.fit(train)

            for row in batch.itertuples():
                # Use the minutes he actually played, so this scores the foul
                # model rather than the minutes model.
                rate, _ = model.player_rate(row.player, as_of)
                opp = model.opponent_factor(row.opponent, as_of)
                mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
                dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))

                observed = float(getattr(row, stat))
                errors.append(abs(dist.mean() - observed))
                for line in lines:
                    line_losses[line].append(mx.log_loss_at_line(dist, observed, line))
                    calib.append((dist.prob_over(line), observed > line))

        if not errors:
            continue
        all_losses = [v for values in line_losses.values() for v in values]
        results.append(
            PlayerResult(
                character=cid,
                market=market,
                n=len(errors),
                mae=float(np.mean(errors)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
                calibration=mx.calibration_buckets(calib),
            )
        )
    return sorted(results, key=lambda r: r.log_loss)


def report(results: list[PlayerResult]) -> str:
    if not results:
        return "no results"
    lines = [
        f"{'character':<14}{'n':>9}{'MAE':>8}{'logloss':>10}{'ECE':>8}"
        f"{'  o0.5':>9}{'o1.5':>8}{'o2.5':>8}",
        "-" * 74,
    ]
    for r in results:
        by = r.log_loss_by_line
        lines.append(
            f"{r.character:<14}{r.n:>9,}{r.mae:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
            f"{by.get(0.5, 0):>9.4f}{by.get(1.5, 0):>8.4f}{by.get(2.5, 0):>8.4f}"
        )
    best = results[0]
    lines.append("")
    lines.append(f"Best: {best.character} (log loss {best.log_loss:.4f}, ECE {best.ece:.4f})")
    return "\n".join(lines)
