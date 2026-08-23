"""Two or three calls per fixture, at different prices, not one or nothing.

One pick at a fixed foul total is over-constrained. Requiring six total fouls
AND better than ten in a hundred is satisfiable once a lineup is confirmed and
almost never before it, so the homepage showed eight picks on a Sunday and none
on a Monday. The bar was not wrong; asking one combination to clear both was.

So each fixture offers a short, a middle and a long option, each the boldest
read available at that price, with the foul total it reaches stated rather than
fixed. A reader can see that the long one is long.
"""

import pytest

from foulgorithm.publish import player_round as pr


def leg(player, fouls, prob, pack=None):
    return {
        "player": player,
        "fullName": f"{player} F",
        "fouls": fouls,
        "line": fouls - 0.5,
        "market": "committed",
        "prob": prob,
        "packProb": pack if pack is not None else prob - 0.05,
        "outOf100": round(prob * 100),
    }


def slip(target, label, legs, prob):
    return {
        "target": target,
        "targetLabel": label,
        "legs": legs,
        "probability": prob,
        "outOf100": round(prob * 100),
        "actualOdds": round(1 / prob, 2),
        "legCount": len(legs),
    }


def by_character():
    return {
        "alan": [
            slip(2.0, "2/1", [leg("A", 1, 0.62)], 0.34),
            slip(5.0, "5/1", [leg("A", 2, 0.4), leg("B", 2, 0.35)], 0.14),
            slip(20.0, "20/1", [leg("A", 2, 0.4), leg("B", 2, 0.35), leg("C", 2, 0.3)], 0.05),
        ],
        "bdog": [
            slip(3.0, "3/1", [leg("D", 1, 0.7), leg("E", 1, 0.5)], 0.25),
            slip(10.0, "10/1", [leg("D", 2, 0.4), leg("E", 2, 0.3), leg("F", 2, 0.3)], 0.09),
        ],
    }


class TestItAlwaysOffersSomething:
    def test_a_fixture_with_slips_gets_options(self):
        options = pr._fixture_options(by_character())
        assert options, "a fixture with slips must offer at least one call"

    def test_it_offers_more_than_one_price(self):
        options = pr._fixture_options(by_character())
        prices = {o["odds"] for o in options}
        assert len(prices) > 1, "two options at the same price is one option"

    def test_it_caps_at_three(self):
        assert len(pr._fixture_options(by_character())) <= 3

    def test_an_empty_fixture_offers_nothing_rather_than_a_blank(self):
        assert pr._fixture_options({}) == []

    def test_options_run_short_price_to_long(self):
        options = pr._fixture_options(by_character())
        assert options == sorted(options, key=lambda o: o["odds"])


class TestEachOptionIsHonest:
    def test_every_option_states_its_foul_total(self):
        for option in pr._fixture_options(by_character()):
            assert option["totalFouls"] == sum(l["fouls"] for l in option["legs"])

    def test_every_option_names_who_made_it(self):
        for option in pr._fixture_options(by_character()):
            assert option["character"] in ("alan", "bdog")

    def test_the_price_matches_the_probability(self):
        for option in pr._fixture_options(by_character()):
            assert option["odds"] == pytest.approx(100 / option["outOf100"], rel=0.2)

    def test_no_option_repeats_another_exactly(self):
        options = pr._fixture_options(by_character())
        seen = {tuple(sorted(l["player"] for l in o["legs"])) + (o["totalFouls"],) for o in options}
        assert len(seen) == len(options)
