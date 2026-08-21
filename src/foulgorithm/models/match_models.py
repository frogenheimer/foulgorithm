"""Match-total-fouls models, in ladder order.

Each must beat the one before it in the walk-forward backtest to be promoted.
Most projects skip to the last one and never learn the second was enough.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import nbinom

from foulgorithm.features import match_features as mf
from foulgorithm.models.base import CountDistribution, register

MAX_FOULS = 60  # the pmf support. Observed maximum across 26 seasons is far below this.

# Marginal variance overstates the model's residual variance, because part of
# that spread is what the team rates now explain. Fitted by sweep, not guessed:
# it cut calibration error from 0.0313 to 0.0067 over 6,080 predictions.
# See docs/modelling-log.md, 2026-08-21.
DEFAULT_DISPERSION_SCALE = 0.65


def negbin_pmf(mean: float, variance: float) -> CountDistribution:
    """A negative binomial as an explicit pmf.

    Fouls are overdispersed: variance exceeds the mean, so Poisson understates
    the tails, and the tails are the part a line is priced on. Falls back to
    Poisson when the data is not overdispersed.
    """
    mean = max(float(mean), 0.1)
    variance = max(float(variance), mean * 1.0001)
    k = np.arange(0, MAX_FOULS + 1)
    r = mean**2 / (variance - mean)
    p = r / (r + mean)
    return CountDistribution(nbinom.pmf(k, r, p))


class _MatchModel:
    market = "match_total_fouls"

    def __init__(
        self,
        half_life_days: float = mf.DEFAULT_HALF_LIFE_DAYS,
        dispersion_scale: float = DEFAULT_DISPERSION_SCALE,
        label: str | None = None,
    ):
        self.half_life_days = half_life_days
        # The marginal variance of totals overstates the model's residual
        # variance, because part of that spread is exactly what the team rates
        # now explain. Using it unscaled makes predictions too timid, which
        # shows up as probabilities compressed toward 0.5. Scale is fitted by
        # the harness rather than guessed. See docs/modelling-log.md, 2026-08-21.
        self.dispersion_scale = dispersion_scale
        self.label = label or self.id
        self._history: pd.DataFrame | None = None
        self._dispersion = 1.3

    def fit(self, train: pd.DataFrame) -> None:
        self._history = train
        totals = train["total_fouls"].to_numpy(dtype=float)
        mean = totals.mean()
        marginal = float(totals.var() / mean)
        self._dispersion = max(1.02, marginal * self.dispersion_scale)

    def config(self) -> dict:
        return {
            "half_life_days": self.half_life_days,
            "dispersion_scale": self.dispersion_scale,
        }

    def _mean(self, row: pd.Series) -> float:
        raise NotImplementedError

    def predict(self, context: pd.DataFrame) -> list[CountDistribution]:
        if self._history is None:
            raise RuntimeError("fit before predict")
        out = []
        for _, row in context.iterrows():
            mean = self._mean(row)
            out.append(negbin_pmf(mean, mean * self._dispersion))
        return out


@register
class LeagueMean(_MatchModel):
    """Every match gets the time-decayed league average. Deliberately stupid.

    Exists to floor the metrics and to prove the harness works. Any model that
    cannot beat this is broken.
    """

    id = "league_mean"
    version = "1.0.0"

    def _mean(self, row: pd.Series) -> float:
        return self._context(row).league_fouls

    def _context(self, row: pd.Series) -> mf.MatchContext:
        return mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            None,
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )


@register
class TeamRates(_MatchModel):
    """Shrunk, time-decayed team rates in the Dixon-Coles multiplicative form.

    Home fouls are driven by how much the home side fouls and how much the away
    side draws fouls. Two shrunk factors per side, not the four unshrunk ones
    the 2025 version stacked.
    """

    id = "team_rates"
    version = "1.0.0"

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            None,
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        home = side * np.sqrt(ctx.home_commit * ctx.away_drawn)
        away = side * np.sqrt(ctx.away_commit * ctx.home_drawn)
        return home + away


@register
class TeamRatesReferee(TeamRates):
    """Team rates plus a heavily shrunk referee factor."""

    id = "team_rates_referee"
    version = "1.0.0"

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        base = side * np.sqrt(ctx.home_commit * ctx.away_drawn) + side * np.sqrt(
            ctx.away_commit * ctx.home_drawn
        )
        return base * ctx.referee_factor


@register
class TeamRatesRefereeMarket(TeamRates):
    """Adds the market's view of how lopsided the fixture is.

    A heavy underdog defends for 90 minutes, and defending is when fouls happen.
    The coefficient is fitted on the training window rather than guessed.
    """

    id = "team_rates_referee_market"
    version = "1.0.0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._market_coef = 0.0

    def config(self) -> dict:
        return {**super().config(), "market_coef": round(float(self._market_coef), 4)}

    def fit(self, train: pd.DataFrame) -> None:
        super().fit(train)
        priced = train.dropna(subset=["odds_home", "odds_draw", "odds_away"])
        if len(priced) < 200:
            self._market_coef = 0.0
            return
        mismatch = np.array(
            [
                mf.mismatch_from_odds(r.odds_home, r.odds_draw, r.odds_away)
                for r in priced.itertuples()
            ]
        )
        totals = priced["total_fouls"].to_numpy(dtype=float)
        # Simple least-squares slope of fouls on mismatch, in relative terms.
        centred = mismatch - mismatch.mean()
        denom = float((centred**2).sum())
        slope = float((centred * (totals - totals.mean())).sum() / denom) if denom else 0.0
        self._market_coef = slope / totals.mean()

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            odds=(row.get("odds_home"), row.get("odds_draw"), row.get("odds_away")),
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        base = side * np.sqrt(ctx.home_commit * ctx.away_drawn) + side * np.sqrt(
            ctx.away_commit * ctx.home_drawn
        )
        return base * ctx.referee_factor * (1.0 + self._market_coef * ctx.mismatch)
