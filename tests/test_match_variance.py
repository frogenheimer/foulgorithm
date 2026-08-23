"""Canary for the match-variance measurement.

This measurement decides whether to ship a correction to every published match
total, so it needs to be checked against data whose answer is known in advance.
The project already carries three negative results from corrections applied
without one, and `docs/25-match-variance.md` warns that marginal variance is not
residual variance, a trap it has fallen into twice.
"""

import numpy as np
import pytest

from foulgorithm.backtest.match_variance_study import decompose


def simulate(n=4000, mean_total=21.5, dispersion=1.25, shared_sd=0.0, seed=1):
    """Matches with a KNOWN shared factor, so the answer is checkable.

    Each match gets a multiplier with mean 1 and the given sd, then a total
    drawn around that. `shared_sd=0` is the null: nothing shared to find.
    """
    rng = np.random.default_rng(seed)
    # Predicted totals vary a little between matches, as the real ones do.
    predicted = rng.normal(mean_total, 1.1, n).clip(5, None)
    variance = predicted * dispersion

    multiplier = rng.normal(1.0, shared_sd, n) if shared_sd else np.ones(n)
    actual = rng.normal(predicted * multiplier, np.sqrt(variance))
    return predicted, variance, actual


class TestTheNull:
    """No shared factor in the data means none reported."""

    def test_it_finds_nothing_when_there_is_nothing(self):
        result = decompose(*simulate(shared_sd=0.0))
        assert result.shared_sd == 0.0

    def test_the_model_variance_matches_the_residual(self):
        result = decompose(*simulate(shared_sd=0.0))
        assert result.model_variance == pytest.approx(result.residual_variance, rel=0.1)


class TestItRecoversAKnownFactor:
    @pytest.mark.parametrize("truth", [0.05, 0.10, 0.20])
    def test_a_planted_shared_factor_comes_back(self, truth):
        result = decompose(*simulate(shared_sd=truth, n=20000))
        assert result.shared_sd == pytest.approx(truth, rel=0.15), (
            f"planted {truth}, recovered {result.shared_sd}"
        )

    def test_a_bigger_factor_reads_bigger(self):
        small = decompose(*simulate(shared_sd=0.05, n=20000)).shared_sd
        large = decompose(*simulate(shared_sd=0.20, n=20000)).shared_sd
        assert large > small * 2


class TestTheSlope:
    def test_a_correctly_scaled_prediction_gives_one(self):
        """The prediction IS the conditional mean, so the slope is 1."""
        rng = np.random.default_rng(7)
        predicted = rng.normal(21.5, 5.0, 8000).clip(5, None)
        variance = predicted * 1.25
        actual = rng.normal(predicted, np.sqrt(variance))
        assert decompose(predicted, variance, actual).slope == pytest.approx(1.0, abs=0.05)

    def test_an_under_discriminating_prediction_gives_more_than_one(self):
        """Predictions squeezed toward their mean, outcomes not."""
        rng = np.random.default_rng(7)
        truth = rng.normal(21.5, 5.0, 8000).clip(5, None)
        predicted = 21.5 + (truth - 21.5) * 0.5   # half the spread it should have
        variance = predicted * 1.25
        actual = rng.normal(truth, np.sqrt(variance))
        assert decompose(predicted, variance, actual).slope > 1.7


class TestTheTrapItIsMeantToAvoid:
    def test_a_wide_outcome_spread_alone_does_not_imply_a_shared_factor(self):
        """Marginal variance is not residual variance.

        Outcomes varying far more than predictions is what a calibrated model
        looks like when most of the variation is genuinely unpredictable. Only
        the part the model's OWN variance fails to cover is a missing factor.
        """
        predicted, variance, actual = simulate(shared_sd=0.0, n=20000)
        result = decompose(predicted, variance, actual)
        assert result.actual_sd > result.predicted_sd * 3, "outcomes do vary much more"
        assert result.shared_sd == 0.0, "and none of it is a shared factor"
