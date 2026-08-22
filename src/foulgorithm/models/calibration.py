"""Correct known overconfidence before publishing a probability.

The backtest found the model systematically overstates the high lines, and
worst at exactly the line where value would live. At 3+ fouls committed it said
24% where 18.4% happened, and 34% where 29.8% happened.

That matters more than it sounds. An overstated probability produces fair odds
that are too short, so a bet that looks like value is not, and the error runs in
the direction that loses money rather than the direction that costs a bet.

The correction shrinks each probability toward its base rate:

    corrected = base + (raw - base) * k

with `k` fitted by least squares on 13,993 walk-forward predictions per market.
k = 1.0 means the raw number was already honest. Fouls drawn is close to that.
Fouls committed at the 3+ line sits at 0.78, so a quarter of its distance from
the base rate was noise.

This is deliberately the simplest correction that fits the observed error. A
richer one (isotonic, per-bucket) would fit the tail more closely and would also
be fitting 64 observations in the top bucket, which is how you end up correcting
noise with more noise.
"""

from __future__ import annotations

import json
from pathlib import Path

CALIBRATION = Path("data/reference/calibration.json")

_cache: dict | None = None


def _table() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(CALIBRATION.read_text()) if CALIBRATION.exists() else {}
    return _cache


def correct(probability: float, market: str, line: float) -> float:
    """Apply the fitted correction. Unknown market or line passes through."""
    entry = _table().get(market, {}).get(str(line))
    if not entry:
        return probability
    base, shrink = entry["base"], entry["shrink"]
    return float(min(max(base + (probability - base) * shrink, 0.001), 0.999))


def factor(market: str, line: float) -> float | None:
    entry = _table().get(market, {}).get(str(line))
    return entry["shrink"] if entry else None
