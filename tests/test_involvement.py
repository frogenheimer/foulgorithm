"""Foul involvements: committed plus won, as one number.

The natural way to build this is to convolve the two distributions, which
assumes a player's fouls committed and fouls won are independent. Measured over
59,649 player-matches of 60 minutes or more, they are not: they correlate at
+0.135, and the variance of the sum runs 13.5% above what independence predicts.

Correcting for that made the model worse, because 13.5% is population variance
and the model already accounts for the spread between players. What is left over
is close to independent. The plain convolution ships; the widening parameter
survives only so the finding can be re-tested.
"""

import pytest

from foulgorithm.models import involvement
from foulgorithm.models.base import CountDistribution


def certain(k: int) -> CountDistribution:
    p = [0.0] * (k + 1)
    p[k] = 1.0
    return CountDistribution(p)


class TestCombine:
    def test_two_certainties_add(self):
        d = involvement.combine(certain(2), certain(3), widen=1.0)
        assert d.pmf(5) == pytest.approx(1.0)

    def test_the_mean_is_the_sum_of_the_means(self):
        # Widening moves the spread and must never move the centre. If it moves
        # the mean it is a different prediction, not a better-shaped one.
        a = CountDistribution([0.3, 0.4, 0.2, 0.1])
        b = CountDistribution([0.5, 0.3, 0.2])
        for widen in (1.0, 1.135, 1.5):
            assert involvement.combine(a, b, widen=widen).mean() == pytest.approx(
                a.mean() + b.mean(), abs=1e-6
            )

    def test_widening_fattens_the_tail(self):
        a = CountDistribution([0.3, 0.4, 0.2, 0.1])
        b = CountDistribution([0.5, 0.3, 0.2])
        plain = involvement.combine(a, b, widen=1.0)
        wide = involvement.combine(a, b, widen=1.4)
        assert wide.prob_over(3.5) > plain.prob_over(3.5)
        assert wide.pmf(0) > plain.pmf(0), "both tails, not just the upper one"

    def test_probabilities_sum_to_one(self):
        a = CountDistribution([0.3, 0.4, 0.2, 0.1])
        b = CountDistribution([0.5, 0.3, 0.2])
        d = involvement.combine(a, b, widen=1.135)
        assert sum(d.pmf(k) for k in range(40)) == pytest.approx(1.0, abs=1e-9)

    def test_widening_below_one_is_refused(self):
        # Narrowing would claim more precision than either input had.
        with pytest.raises(ValueError):
            involvement.combine(certain(1), certain(1), widen=0.8)


@pytest.mark.network
class TestAgainstReality:
    def test_the_widening_factor_is_measured_not_chosen(self):
        f = involvement.dispersion_inflation()
        assert 1.05 < f < 1.30

    def test_what_ships_is_the_plain_convolution(self):
        # Guard on the negative result. Defaulting this back to the measured
        # factor would look like a correction and score worse.
        assert involvement.DEFAULT_WIDEN == 1.0
