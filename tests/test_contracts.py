"""Tests for the market and model contracts.

These are the foundations everything else is built on, so they get tested first.
"""

import numpy as np
import pytest

from foulgorithm.markets import base as markets
from foulgorithm.models.base import BinaryDistribution, CountDistribution


class TestMarketSpecs:
    def test_launch_markets_are_registered(self):
        keys = set(markets.all_markets())
        assert keys == {"player_fouls_committed", "player_tackles", "player_cards"}

    def test_cards_is_binary_not_count(self):
        # Cards look like a count and are not one. See docs/05-markets.md.
        assert markets.get("player_cards").family == "binary"
        assert markets.get("player_fouls_committed").family == "count"

    def test_whole_number_lines_are_rejected(self):
        # A whole-number line can push, which we have no way to price.
        with pytest.raises(ValueError, match="whole number"):
            markets.MarketSpec(
                key="bad",
                label="Bad",
                entity="player",
                family="count",
                stat_column="x",
                lines=(2.0,),
                settlement_note="",
            )

    def test_binary_market_takes_one_line(self):
        with pytest.raises(ValueError, match="exactly one line"):
            markets.MarketSpec(
                key="bad_binary",
                label="Bad",
                entity="player",
                family="binary",
                stat_column="x",
                lines=(0.5, 1.5),
                settlement_note="",
            )

    def test_unknown_market_raises(self):
        with pytest.raises(KeyError):
            markets.get("player_headers_won")


class TestCountDistribution:
    def test_normalises_input(self):
        d = CountDistribution([2.0, 2.0])
        assert d.pmf(0) == pytest.approx(0.5)
        assert d.pmf(1) == pytest.approx(0.5)

    def test_prob_over_matches_manual_sum(self):
        d = CountDistribution([0.3, 0.4, 0.2, 0.1])
        assert d.prob_over(1.5) == pytest.approx(0.3)  # P(2) + P(3)
        assert d.prob_over(0.5) == pytest.approx(0.7)
        assert d.prob_under(1.5) == pytest.approx(0.7)

    def test_fair_odds_is_reciprocal(self):
        d = CountDistribution([0.5, 0.5])
        assert d.fair_odds_over(0.5) == pytest.approx(2.0)

    def test_mean(self):
        d = CountDistribution([0.5, 0.5])
        assert d.mean() == pytest.approx(0.5)

    def test_out_of_range_pmf_is_zero(self):
        d = CountDistribution([1.0])
        assert d.pmf(5) == 0.0
        assert d.pmf(-1) == 0.0

    def test_whole_number_line_rejected(self):
        d = CountDistribution([0.5, 0.5])
        with pytest.raises(ValueError, match="whole number"):
            d.prob_over(1.0)

    @pytest.mark.parametrize("bad", [[], [-0.1, 0.5], [0.0, 0.0]])
    def test_invalid_input_raises(self, bad):
        with pytest.raises(ValueError):
            CountDistribution(bad)

    def test_probabilities_sum_to_one(self):
        d = CountDistribution(np.array([1.0, 3.0, 6.0]))
        assert sum(d.to_list()) == pytest.approx(1.0)


class TestBinaryDistribution:
    def test_prob_over_half_is_p(self):
        d = BinaryDistribution(0.2)
        assert d.prob_over(0.5) == pytest.approx(0.2)
        assert d.mean() == pytest.approx(0.2)

    def test_serialises_both_outcomes(self):
        assert BinaryDistribution(0.25).to_list() == pytest.approx([0.75, 0.25])

    @pytest.mark.parametrize("bad", [-0.01, 1.01])
    def test_out_of_range_p_raises(self, bad):
        with pytest.raises(ValueError):
            BinaryDistribution(bad)

    def test_zero_probability_gives_infinite_odds(self):
        assert BinaryDistribution(0.0).fair_odds_over(0.5) == float("inf")
