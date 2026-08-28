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


def calibration_buckets(pairs: list[tuple[float, bool]], n_buckets: int = 10) -> list[dict]:
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
    return float(sum(b["n"] * abs(b["predicted"] - b["observed"]) for b in buckets) / total)


def pit(dist: CountDistribution, observed: float, rng: np.random.Generator) -> float:
    """Randomised probability integral transform for a count outcome.

    From a correct model these are uniform on [0, 1]. Mass piling into the
    tails means outcomes run wider than the model says; mass piling into the
    middle means the model is too wide. This is the whole-distribution view
    of calibration the per-line corrections cannot give, and the
    randomisation is what makes PIT exact for discrete outcomes, so the
    generator is passed in rather than created here: the evidence pack has to
    reproduce.
    """
    k = int(observed)
    lower = dist.cdf(k - 1) if k > 0 else 0.0
    return float(min(max(lower + rng.uniform() * dist.pmf(k), 0.0), 1.0))


def interval_coverage(pairs: list[tuple[CountDistribution, float]], level: float = 0.9) -> dict:
    """Did the stated central interval hold its stated share of outcomes?

    Discrete support makes an exact 90% interval impossible, so the interval
    is the tightest one holding AT LEAST the level, and `nominal` reports the
    probability it actually holds. Achieved is judged against nominal, never
    against the requested level, so the discreteness gap cannot be mistaken
    for miscalibration.
    """
    tail = (1.0 - level) / 2.0
    inside = below = above = 0
    nominal_total = 0.0

    for dist, observed in pairs:
        p = dist.probabilities()
        cdf = np.cumsum(p)
        # The epsilon settles exact boundaries: a lower region holding exactly
        # the tail mass is dropped, which keeps the interval the tightest one
        # holding at least the level rather than drifting a bin wide on
        # floating-point noise.
        lo = int(np.searchsorted(cdf, tail + 1e-9, side="right"))
        hi = int(np.searchsorted(cdf, 1.0 - tail - 1e-9, side="left"))
        nominal_total += float(cdf[hi] - (cdf[lo - 1] if lo > 0 else 0.0))
        if observed < lo:
            below += 1
        elif observed > hi:
            above += 1
        else:
            inside += 1

    n = len(pairs)
    return {
        "level": level,
        "nominal": round(nominal_total / n, 4) if n else float("nan"),
        "achieved": round(inside / n, 4) if n else float("nan"),
        "below": round(below / n, 4) if n else float("nan"),
        "above": round(above / n, 4) if n else float("nan"),
        "n": n,
    }


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
