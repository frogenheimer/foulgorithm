"""The model contract.

Two rules make the rest of the system work:

1. predict() returns a Distribution, never a number. Every published line and every
   fair price derives from it.
2. fit() only ever sees rows the harness handed it. Models never read the database,
   which is how leakage is prevented centrally rather than trusted to each author.

See docs/06-modelling.md and docs/decisions/ADR-005-distributions-not-estimates.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    import pandas as pd


class Distribution(Protocol):
    """A predicted distribution over a market outcome."""

    def pmf(self, k: int) -> float: ...
    def cdf(self, k: int) -> float: ...
    def mean(self) -> float: ...

    def prob_over(self, line: float) -> float:
        """P(outcome > line). Lines are half-values, so there is no push to handle."""
        ...

    def fair_odds_over(self, line: float) -> float:
        """Decimal price implied by prob_over, with no margin."""
        ...


class _BaseDistribution:
    """Shared derivations. Subclasses provide pmf and mean."""

    def cdf(self, k: int) -> float:
        return float(sum(self.pmf(i) for i in range(0, k + 1)))

    def prob_over(self, line: float) -> float:
        if line * 2 % 2 == 0:
            raise ValueError(f"line {line} is a whole number, use half-lines")
        return float(max(0.0, min(1.0, 1.0 - self.cdf(int(np.floor(line))))))

    def prob_under(self, line: float) -> float:
        return 1.0 - self.prob_over(line)

    def fair_odds_over(self, line: float) -> float:
        p = self.prob_over(line)
        if p <= 0.0:
            return float("inf")
        return 1.0 / p


class CountDistribution(_BaseDistribution):
    """A distribution over non-negative counts, held as an explicit pmf.

    Storing the pmf rather than parameters means the site can render the full shape
    and any model family can produce one.
    """

    def __init__(self, probabilities: np.ndarray | list[float]):
        p = np.asarray(probabilities, dtype=float)
        if p.ndim != 1 or len(p) == 0:
            raise ValueError("probabilities must be a non-empty 1d array")
        if np.any(p < 0):
            raise ValueError("probabilities must be non-negative")
        total = p.sum()
        if not np.isfinite(total) or total <= 0:
            raise ValueError("probabilities must sum to a positive finite value")
        self._p = p / total

    def probabilities(self) -> np.ndarray:
        """The pmf as an array. Lets distributions be mixed without re-deriving."""
        return self._p.copy()

    def pmf(self, k: int) -> float:
        if k < 0 or k >= len(self._p):
            return 0.0
        return float(self._p[k])

    def cdf(self, k: int) -> float:
        if k < 0:
            return 0.0
        return float(self._p[: k + 1].sum())

    def mean(self) -> float:
        return float((np.arange(len(self._p)) * self._p).sum())

    def to_list(self) -> list[float]:
        """Serialisation format for the predictions table."""
        return [float(x) for x in self._p]


class BinaryDistribution(_BaseDistribution):
    """A Bernoulli outcome. Used for card markets."""

    def __init__(self, p: float):
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0, 1], got {p}")
        self._p = float(p)

    def pmf(self, k: int) -> float:
        if k == 1:
            return self._p
        if k == 0:
            return 1.0 - self._p
        return 0.0

    def cdf(self, k: int) -> float:
        if k < 0:
            return 0.0
        if k == 0:
            return 1.0 - self._p
        return 1.0

    def mean(self) -> float:
        return self._p

    def to_list(self) -> list[float]:
        return [1.0 - self._p, self._p]


@runtime_checkable
class Model(Protocol):
    id: str
    version: str
    market: str

    def fit(self, train: pd.DataFrame) -> None: ...
    def predict(self, context: pd.DataFrame) -> list[Distribution]: ...

    def config(self) -> dict:
        """Hyperparameters. Hashed into model_runs so runs are distinguishable."""
        ...


_REGISTRY: dict[tuple[str, str], type] = {}


def register(cls: type) -> type:
    """Class decorator. Registers a model under (id, version)."""
    for attr in ("id", "version", "market"):
        if not getattr(cls, attr, None):
            raise TypeError(f"{cls.__name__} must define a non-empty {attr!r}")
    key = (cls.id, cls.version)
    if key in _REGISTRY:
        raise ValueError(f"model {key} is already registered")
    _REGISTRY[key] = cls
    return cls


def get(model_id: str, version: str) -> type:
    key = (model_id, version)
    if key not in _REGISTRY:
        raise KeyError(f"unknown model {key}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def for_market(market_key: str) -> list[type]:
    return [c for c in _REGISTRY.values() if c.market == market_key]


def all_models() -> dict[tuple[str, str], type]:
    return dict(_REGISTRY)
