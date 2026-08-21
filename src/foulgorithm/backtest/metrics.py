"""Scoring rules.

Probabilistic quality decides promotion. Betting returns are reported but never
promote a model on their own, because a few hundred results are mostly noise
while calibration is not.
"""

from __future__ import annotations

import numpy as np

from foulgorithm.models.base import CountDistribution

EPS = 1e-9


def log_loss_at_line(dist: CountDistribution, observed: float, line: float) -> float:
    """Negative log likelihood of the over/under outcome at one line."""
    p_over = min(max(dist.prob_over(line), EPS), 1 - EPS)
    went_over = observed > line
    return -np.log(p_over if went_over else 1 - p_over)


def brier_at_line(dist: CountDistribution, observed: float, line: float) -> float:
    p_over = dist.prob_over(line)
    return float((p_over - (1.0 if observed > line else 0.0)) ** 2)


def crps(dist: CountDistribution, observed: float) -> float:
    """Continuous ranked probability score for a count distribution.

    Scores the whole predicted distribution against the realised value rather
    than one threshold, so a model cannot look good by being right about a
    single line while being wrong about the shape.
    """
    k = np.arange(0, 61)
    cdf = np.array([dist.cdf(int(i)) for i in k])
    step = (k >= observed).astype(float)
    return float(((cdf - step) ** 2).sum())


def calibration_buckets(
    pairs: list[tuple[float, bool]], n_buckets: int = 10
) -> list[dict]:
    """Predicted probability against observed frequency, bucketed.

    The chart that tells you whether a model means what it says.
    """
    out = []
    edges = np.linspace(0, 1, n_buckets + 1)
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        chosen = [(p, o) for p, o in pairs if lo <= p < hi or (hi == 1.0 and p == 1.0)]
        if not chosen:
            continue
        out.append(
            {
                "lo": round(float(lo), 3),
                "hi": round(float(hi), 3),
                "n": len(chosen),
                "predicted": round(float(np.mean([p for p, _ in chosen])), 4),
                "observed": round(float(np.mean([1.0 if o else 0.0 for _, o in chosen])), 4),
            }
        )
    return out


def expected_calibration_error(pairs: list[tuple[float, bool]], n_buckets: int = 10) -> float:
    buckets = calibration_buckets(pairs, n_buckets)
    total = sum(b["n"] for b in buckets)
    if not total:
        return float("nan")
    return float(
        sum(b["n"] * abs(b["predicted"] - b["observed"]) for b in buckets) / total
    )


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 7) -> tuple[float, float]:
    """95% interval for a mean. Every headline number gets one of these.

    A metric without an interval invites reading noise as a result.
    """
    if not values:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    means = arr[rng.integers(0, len(arr), size=(n, len(arr)))].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))
