"""The direct test of within-match dependence, and the reopen tripwire.

The variance decomposition found no missing shared factor for the house
model, but advisor 2's caveat was accepted: a fitted zero rests on the
model's own conditional variances, so overstated idiosyncratic variance
could cancel against missing positive covariance. This study does not route
through the decomposition at all. It standardises each player's residual by
his own predictive spread and averages pairwise products within matches. If
players genuinely move together beyond what the shared factors already carry,
this reads positive, and the Poisson-lognormal architecture comes back off
the shelf per docs/ideas.md.

These tests plant known dependence and independence and check the estimator
tells them apart, because a dependence test that cannot detect planted
dependence would clear the model of a fault it cannot see.
"""

import numpy as np
import pandas as pd
import pytest

from foulgorithm.backtest import pairwise_dependence_study as pds


def synthetic_matches(shared_sd: float, n_matches: int = 300, seed: int = 7):
    """Player-matches with a planted shared per-match factor.

    Each match draws a multiplier exp(N(0, shared_sd^2)); every player's
    Poisson mean is scaled by it. shared_sd of zero is genuine independence.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for match in range(n_matches):
        factor = float(np.exp(rng.normal(0.0, shared_sd))) if shared_sd else 1.0
        for side in ("home", "away"):
            for player in range(9):
                mean = 1.1 * factor
                rows.append(
                    {
                        "match": match,
                        "team": f"{side}-{match}",
                        "predicted_mean": 1.1 * (np.exp(shared_sd**2 / 2) if shared_sd else 1.0),
                        "predicted_var": None,
                        "observed": float(rng.poisson(mean)),
                    }
                )
    frame = pd.DataFrame(rows)
    # The model's own variance for each prediction: Poisson plus the planted
    # lognormal mixing, which is what a correctly-specified marginal knows.
    m = frame["predicted_mean"]
    extra = (np.exp(shared_sd**2) - 1.0) * m**2 if shared_sd else 0.0
    frame["predicted_var"] = m + extra
    return frame


class TestTheEstimator:
    def test_independence_reads_as_zero(self):
        result = pds.pairwise_correlation(synthetic_matches(shared_sd=0.0))
        assert result["teammates"] == pytest.approx(0.0, abs=0.02)
        assert result["opponents"] == pytest.approx(0.0, abs=0.02)

    def test_a_planted_shared_factor_reads_positive_everywhere(self):
        """A per-match factor moves BOTH teams, so teammate and opponent
        correlations rise together. That signature separates a match effect
        from, say, a team-level one."""
        result = pds.pairwise_correlation(synthetic_matches(shared_sd=0.25))
        assert result["teammates"] > 0.03
        assert result["opponents"] > 0.03

    def test_pair_counts_are_reported(self):
        result = pds.pairwise_correlation(synthetic_matches(shared_sd=0.0, n_matches=10))
        # 9 players a side: 2 * C(9,2) = 72 teammate pairs, 81 opponent pairs.
        assert result["teammate_pairs"] == 72 * 10
        assert result["opponent_pairs"] == 81 * 10

    def test_a_single_player_match_contributes_no_pairs(self):
        frame = pd.DataFrame(
            [
                {"match": 0, "team": "a", "predicted_mean": 1.0, "predicted_var": 1.2, "observed": 2.0},
            ]
        )
        result = pds.pairwise_correlation(frame)
        assert result["teammate_pairs"] == 0
        assert result["opponent_pairs"] == 0


class TestTheBootstrap:
    def test_the_interval_brackets_the_point_estimate(self):
        frame = synthetic_matches(shared_sd=0.25)
        point = pds.pairwise_correlation(frame)["teammates"]
        lo, hi = pds.bootstrap_interval(frame, "teammates", n=200)
        assert lo < point < hi

    def test_independence_produces_an_interval_spanning_zero(self):
        frame = synthetic_matches(shared_sd=0.0)
        lo, hi = pds.bootstrap_interval(frame, "teammates", n=200)
        assert lo < 0.0 < hi

    def test_a_planted_factor_produces_an_interval_clear_of_zero(self):
        """The reopen tripwire has to be able to fire, or a null result from
        it means nothing."""
        frame = synthetic_matches(shared_sd=0.35, n_matches=500)
        lo, _ = pds.bootstrap_interval(frame, "teammates", n=200)
        assert lo > 0.0


class TestJointLegs:
    def test_independent_legs_price_a_double_correctly(self):
        frame = synthetic_matches(shared_sd=0.0, n_matches=400)
        got = pds.two_leg_check(frame, line=0.5)
        assert got["predicted"] == pytest.approx(got["observed"], abs=0.03)

    def test_a_shared_factor_makes_doubles_land_more_often_than_the_product(self):
        frame = synthetic_matches(shared_sd=0.35, n_matches=400)
        got = pds.two_leg_check(frame, line=0.5)
        assert got["observed"] > got["predicted"] + 0.01
