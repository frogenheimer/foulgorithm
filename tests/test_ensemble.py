"""The house model: the five, averaged.

Five characters separate by about 2% and each is wrong in its own direction.
Averaging them is the oldest trick in forecasting and it usually wins, because
the errors are not perfectly correlated and half of each cancels.

It is a SIXTH opinion rather than a judge of the other five, and the site says
so. What it is not is a character: it has no temperament, no weakness worth
naming and nothing to explore. That is the point of it.
"""

import pytest

from foulgorithm.models import ensemble


class TestBlend:
    def test_it_averages(self):
        assert ensemble.blend([0.2, 0.4, 0.6]) == pytest.approx(0.4)

    def test_one_model_is_itself(self):
        assert ensemble.blend([0.37]) == pytest.approx(0.37)

    def test_nothing_to_blend_is_refused(self):
        # Returning a default here would put a made-up number on the front page.
        with pytest.raises(ValueError):
            ensemble.blend([])

    def test_it_stays_a_probability(self):
        for probs in ([0.0, 0.0], [1.0, 1.0], [0.01, 0.99]):
            assert 0.0 <= ensemble.blend(probs) <= 1.0

    def test_weights_are_honoured(self):
        # Equal weights until there is a record to fit them on. The parameter
        # exists so that day does not need a rewrite.
        assert ensemble.blend([0.2, 0.8], weights=[3, 1]) == pytest.approx(0.35)

    def test_mismatched_weights_are_refused(self):
        with pytest.raises(ValueError):
            ensemble.blend([0.2, 0.8], weights=[1, 1, 1])


class TestSlate:
    def test_a_slate_names_its_shape(self):
        s = ensemble.SLATES[0]
        assert s.legs > 0 and s.label

    def test_every_slate_is_a_fixed_shape(self):
        # Comparing characters needs identical difficulty. A slate whose leg
        # count varies is not the same bet twice.
        for s in ensemble.SLATES:
            assert sum(n for _, n in s.shape) == s.legs

    def test_slates_are_distinct(self):
        assert len({s.key for s in ensemble.SLATES}) == len(ensemble.SLATES)


class TestScoring:
    def test_every_leg_landing_is_a_win(self):
        r = ensemble.score_slate([True, True, True])
        assert r["points"] == 3 and r["result"] == "won"

    def test_all_but_one_is_a_draw(self):
        # A near miss is not a wipeout, and scoring them the same throws away
        # most of what separates a good week from a bad one.
        r = ensemble.score_slate([True, True, False])
        assert r["points"] == 1 and r["result"] == "drawn"

    def test_two_missing_is_a_loss(self):
        r = ensemble.score_slate([True, False, False])
        assert r["points"] == 0 and r["result"] == "lost"

    def test_difference_is_legs_landed_minus_missed(self):
        assert ensemble.score_slate([True, True, False])["difference"] == 1
        assert ensemble.score_slate([False, False, False])["difference"] == -3

    def test_an_empty_slate_scores_nothing(self):
        r = ensemble.score_slate([])
        assert r["points"] == 0 and r["result"] == "void"
