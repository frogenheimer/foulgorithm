"""Odds arithmetic, because getting it wrong quietly is worse than most bugs.

The tiers were held as decimal prices and rendered as fractional ones, so a
decimal 2.0, which is evens, was displayed as "2/1". Every tier on the site was
one step longer than it read. Nothing failed; the numbers were simply wrong.

Also carries the bookmaker margin, which compounds per leg. That is why a
bookmaker pushes accumulators: at 15% a leg, a three-leg combination has about
34% taken out of it, not 15%.
"""

import pytest

from foulgorithm.markets import odds


class TestConversion:
    @pytest.mark.parametrize(
        "decimal,fractional",
        [(2.0, "1/1"), (3.0, "2/1"), (4.0, "3/1"), (6.0, "5/1"), (11.0, "10/1"), (21.0, "20/1")],
    )
    def test_decimal_to_fractional(self, decimal, fractional):
        assert odds.fractional(decimal) == fractional

    def test_short_prices_keep_a_readable_fraction(self):
        # 1.5 is 1/2, not "0/1". Odds-on prices are the common case at 0.5 lines.
        assert odds.fractional(1.5) == "1/2"
        assert odds.fractional(1.25) == "1/4"

    def test_probability_round_trips(self):
        for p in (0.05, 0.33, 0.5, 0.9):
            assert odds.to_probability(odds.to_decimal(p)) == pytest.approx(p)


class TestMargin:
    def test_a_single_leg_loses_the_stated_margin(self):
        # Fair 4.0 at a 15% book is offered around 3.48.
        assert odds.offered(4.0, legs=1, margin=0.15) == pytest.approx(4.0 / 1.15, abs=1e-6)

    def test_margin_compounds_across_legs(self):
        # The reason accumulators are pushed. Three legs at 15% is not 15%.
        one = odds.take_out(legs=1, margin=0.15)
        three = odds.take_out(legs=3, margin=0.15)
        assert one == pytest.approx(0.130, abs=0.002)
        assert three == pytest.approx(0.342, abs=0.002)
        assert three > one * 2.5

    def test_five_legs_takes_out_about_half(self):
        assert odds.take_out(legs=5, margin=0.15) == pytest.approx(0.503, abs=0.005)

    def test_zero_margin_changes_nothing(self):
        assert odds.offered(6.0, legs=4, margin=0.0) == pytest.approx(6.0)

    def test_a_negative_margin_is_refused(self):
        # A bookmaker offering better than fair is not a case to model quietly.
        with pytest.raises(ValueError):
            odds.offered(3.0, legs=2, margin=-0.05)


class TestValue:
    def test_a_price_is_worth_taking_only_above_fair_plus_edge(self):
        # Fair 4.0, 10% edge requirement, so 4.40 is the floor.
        assert odds.floor(4.0, edge=0.10) == pytest.approx(4.4)

    def test_the_verdict_is_stated_not_implied(self):
        # Offered below the floor is not value, and the wording says so rather
        # than leaving a reader to compare two numbers.
        assert odds.verdict(fair=4.0, offered=3.4, edge=0.10) == "below fair"
        assert odds.verdict(fair=4.0, offered=4.1, edge=0.10) == "fair, under our margin"
        assert odds.verdict(fair=4.0, offered=4.8, edge=0.10) == "worth taking"
