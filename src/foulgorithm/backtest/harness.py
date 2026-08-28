"""Walk-forward evaluation.

The most important component in the repository. It is the only thing standing
between us and confidently shipping a model that does not work.

Protocol, for each weekly batch of fixtures:
  1. as_of is the earliest kickoff in the batch
  2. training rows are those with known_at <= as_of, and nothing else
  3. fit, predict the batch, score, advance

Models never see the store, so they cannot reach past the filter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx

DEFAULT_LINES = (20.5, 22.5, 24.5, 26.5)


@dataclass
class Result:
    model_id: str
    version: str
    config: dict
    n: int
    mae: float
    mae_ci: tuple[float, float]
    crps: float
    log_loss: float
    log_loss_by_line: dict[float, float]
    ece: float
    calibration: list[dict] = field(default_factory=list)

    def row(self) -> dict:
        return {
            "model": self.model_id,
            "n": self.n,
            "MAE": round(self.mae, 3),
            "CRPS": round(self.crps, 3),
            "logloss": round(self.log_loss, 4),
            "ECE": round(self.ece, 4),
        }


def walk_forward(
    model_classes: list,
    matches: pd.DataFrame,
    start: str,
    lines: tuple[float, ...] = DEFAULT_LINES,
    min_train: int = 760,
) -> list[Result]:
    """Evaluate every model on identical data under identical rules.

    Entries may be classes or already-constructed instances, so a hyperparameter
    sweep is just a list of instances rather than a class per value.
    """
    matches = matches.sort_values("kickoff_utc").reset_index(drop=True)
    evaluation = matches[matches["season"] >= start]
    if evaluation.empty:
        raise ValueError(f"no matches at or after {start}")

    # Weekly batches, computed without dropping timezone information.
    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    results = []

    for entry in model_classes:
        model = entry() if isinstance(entry, type) else entry
        errors: list[float] = []
        crps_scores: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
            train = matches[matches["known_at"] <= as_of]
            if len(train) < min_train:
                continue

            model.fit(train)
            distributions = model.predict(batch)

            for dist, observed in zip(distributions, batch["total_fouls"], strict=True):
                observed = float(observed)
                errors.append(abs(dist.mean() - observed))
                crps_scores.append(mx.crps(dist, observed))
                for line in lines:
                    line_losses[line].append(mx.log_loss_at_line(dist, observed, line))
                    calib.append((dist.prob_over(line), observed > line))

        if not errors:
            continue

        all_losses = [v for values in line_losses.values() for v in values]
        results.append(
            Result(
                model_id=getattr(model, "label", model.id),
                version=model.version,
                config=model.config(),
                n=len(errors),
                mae=float(np.mean(errors)),
                mae_ci=mx.bootstrap_ci(errors),
                crps=float(np.mean(crps_scores)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
                calibration=mx.calibration_buckets(calib),
            )
        )

    return sorted(results, key=lambda r: r.log_loss)


def report(results: list[Result]) -> str:
    lines = [
        f"{'model':<28}{'n':>7}{'MAE':>8}{'CRPS':>8}{'logloss':>10}{'ECE':>8}",
        "-" * 69,
    ]
    for r in results:
        lines.append(
            f"{r.model_id:<28}{r.n:>7}{r.mae:>8.3f}{r.crps:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
        )

    if results:
        best, base = results[0], next((r for r in results if r.model_id == "league_mean"), None)
        if base and best.model_id != base.model_id:
            gain = (base.log_loss - best.log_loss) / base.log_loss * 100
            lines.append("")
            lines.append(
                f"Best: {best.model_id}, {gain:.2f}% better log loss than the league-mean baseline."
            )
            lines.append(
                f"  MAE 95% CI {best.mae_ci[0]:.3f} to {best.mae_ci[1]:.3f} "
                f"(baseline {base.mae:.3f})"
            )
    return "\n".join(lines)
