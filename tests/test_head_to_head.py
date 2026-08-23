"""Valentina's actual method, rather than a parameter that stands in for one.

She is described as the character who reads the matchup. What that meant until
now was an opponent weight of 1.6, which is not reading anything: it is the same
calculation as everyone else's with one number turned up. This gives her a
question the other four do not ask, namely whether THESE TWO CLUBS produce more
fouls than their own rates imply.

The effect is real and small. Across 9,120 matches and 428 pairings with eight
or more meetings, splitting each pairing's history in half and correlating the
two halves gives +0.138. The spread of pairing means is 2.17 fouls where noise
alone would give 1.90, so the true pairing effect is about 1.06 fouls on a base
near 21, roughly 5%.

A split-half correlation of 0.138 is a reliability of about 0.24 by
Spearman-Brown, so about three quarters of any observed pairing residual is
noise and gets shrunk away. Shipping the raw residual would be the same mistake
as taking a promoted club's Championship rate at face value.
"""

import pytest

from foulgorithm.features import head_to_head as h2h


class TestShrinkage:
    def test_a_pairing_never_seen_has_no_adjustment(self):
        # Not "average", which would be a claim. Nothing is known.
        assert h2h.adjustment("Arsenal", "Coventry", {}) == 1.0

    def test_one_meeting_barely_moves_the_number(self):
        # A single hot match is the least reliable evidence there is.
        seen = {("Arsenal", "Chelsea"): [10.0]}
        adj = h2h.adjustment("Arsenal", "Chelsea", seen)
        assert 1.0 < adj < 1.06, "one meeting should be almost entirely shrunk away"

    def test_more_meetings_move_it_further(self):
        few = h2h.adjustment("A", "B", {("A", "B"): [6.0]})
        many = h2h.adjustment("A", "B", {("A", "B"): [6.0] * 12})
        assert many > few

    def test_even_a_long_history_stays_modest(self):
        # Reliability caps at about 0.24. A pairing running 6 fouls hot across
        # twenty meetings is still only worth a few percent.
        adj = h2h.adjustment("A", "B", {("A", "B"): [6.0] * 20})
        assert 1.0 < adj < 1.10, f"{adj} claims more than the measurement supports"

    def test_it_works_in_both_directions(self):
        assert h2h.adjustment("A", "B", {("A", "B"): [-6.0] * 20}) < 1.0

    def test_the_pair_key_ignores_venue(self):
        # Arsenal v Chelsea and Chelsea v Arsenal are the same pairing. Keying
        # on order would halve every sample and double the noise.
        assert h2h.pair_key("Arsenal", "Chelsea") == h2h.pair_key("Chelsea", "Arsenal")


class TestReliability:
    def test_the_reliability_is_measured_not_chosen(self):
        assert 0.1 < h2h.RELIABILITY < 0.45

    def test_a_zero_residual_pairing_is_neutral(self):
        assert h2h.adjustment("A", "B", {("A", "B"): [0.0] * 10}) == pytest.approx(1.0)
