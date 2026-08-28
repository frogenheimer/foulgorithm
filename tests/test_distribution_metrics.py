"""PIT and interval coverage, the two distribution checks the audit asked for.

Threshold metrics score one line at a time; these score the whole shape. A
randomised PIT from a correct model is uniform on [0, 1], and a stated 90%
interval from a correct model covers about 90% of outcomes. Both are demanded
by the calibration apparatus in docs/34-final-plan.md, item A2, and both must
behave deterministically under a seeded generator or the evidence pack stops
being reproducible.
"""

import numpy as np
import pytest

from foulgorithm.backtest import metrics as mx
from foulgorithm.models.base import CountDistribution
from foulgorithm.models.match_models import negbin_pmf


def sample_from(dist, n, rng):
    p = dist.probabilities()
    return rng.choice(np.arange(len(p)), size=n, p=p / p.sum())


class TestPit:
    def test_a_correct_model_produces_a_uniform_pit(self):
        rng = np.random.default_rng(7)
        dist = negbin_pmf(1.2, 1.5)
        values = [mx.pit(dist, float(y), rng) for y in sample_from(dist, 4000, rng)]
        assert np.mean(values) == pytest.approx(0.5, abs=0.02)
        assert np.std(values) == pytest.approx(np.sqrt(1 / 12), abs=0.02)
        assert min(values) >= 0.0 and max(values) <= 1.0

    def test_an_overconfident_model_piles_into_the_tails(self):
        """Outcomes wider than the model says push PIT mass toward 0 and 1,
        which is exactly the signature the calibration re-audit looks for."""
        rng = np.random.default_rng(7)
        narrow = negbin_pmf(1.2, 1.21)
        wide = negbin_pmf(1.2, 3.0)
        values = np.array([mx.pit(narrow, float(y), rng) for y in sample_from(wide, 4000, rng)])
        tails = ((values < 0.1) | (values > 0.9)).mean()
        assert tails > 0.25

    def test_seeded_means_reproducible(self):
        dist = negbin_pmf(1.2, 1.5)
        one = mx.pit(dist, 2.0, np.random.default_rng(11))
        two = mx.pit(dist, 2.0, np.random.default_rng(11))
        assert one == two


class TestIntervalCoverage:
    def test_the_interval_is_read_off_the_distribution(self):
        dist = CountDistribution([0.05, 0.90, 0.05])
        got = mx.interval_coverage([(dist, 1.0)], level=0.9)
        assert got["achieved"] == 1.0

    def test_misses_are_split_by_side(self):
        dist = CountDistribution([0.05, 0.90, 0.05])
        got = mx.interval_coverage([(dist, 0.0), (dist, 1.0), (dist, 1.0), (dist, 2.0)], level=0.9)
        assert got["achieved"] == 0.5
        assert got["below"] == 0.25
        assert got["above"] == 0.25
        assert got["n"] == 4

    def test_a_correct_model_covers_about_its_stated_level(self):
        rng = np.random.default_rng(7)
        dist = negbin_pmf(1.5, 2.2)
        pairs = [(dist, float(y)) for y in sample_from(dist, 4000, rng)]
        got = mx.interval_coverage(pairs, level=0.9)
        # Discrete support makes exact 90% impossible; the nominal level the
        # interval actually holds is reported so the gap is attributable.
        assert got["achieved"] >= 0.9
        assert got["achieved"] == pytest.approx(got["nominal"], abs=0.02)

    def test_a_too_narrow_model_undercovers(self):
        rng = np.random.default_rng(7)
        narrow = negbin_pmf(1.5, 1.51)
        wide = negbin_pmf(1.5, 4.0)
        pairs = [(narrow, float(y)) for y in sample_from(wide, 4000, rng)]
        got = mx.interval_coverage(pairs, level=0.9)
        assert got["achieved"] < got["nominal"] - 0.03
