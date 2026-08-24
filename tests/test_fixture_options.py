"""The fixture card shows the crossover, not one temperament's reach.

Oliver's call, 2026-08-24: the card carries the picks the five most agree
on, ranked by how many of them back each leg, priced by the house blend, and
representing no specific model. These tests pin the counting rules that make
"4 of 5 back this" mean what it says: a character backs a leg once however
many tiers of his ladder repeat it, ranking is backers first and house
number second, and the card says plainly when it was built before the team
sheets landed.
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
    """Two characters. A is backed by both; B only by alan, and twice over
    in alan's ladder, which must still count him once."""
    return {
        "alan": [
            slip(2.0, "2/1", [leg("A", 1, 0.62), leg("B", 2, 0.40)], 0.25),
            slip(5.0, "5/1", [leg("B", 2, 0.40), leg("C", 2, 0.35)], 0.14),
        ],
        "bdog": [
            slip(3.0, "3/1", [leg("A", 1, 0.58), leg("D", 1, 0.50)], 0.29),
        ],
    }


class TestTheCrossover:
    def test_one_card_never_a_specific_character(self):
        options = pr._fixture_options(by_character())
        assert len(options) == 1
        assert options[0]["character"] == "consensus"
        assert options[0]["characterName"] == "The five"

    def test_legs_rank_by_backers_then_house(self):
        legs = pr._fixture_options(by_character())[0]["legs"]
        assert legs[0]["player"] == "A"
        assert legs[0]["backers"] == 2
        assert [l["backers"] for l in legs] == sorted(
            [l["backers"] for l in legs], reverse=True
        )

    def test_a_ladder_repeating_a_leg_backs_it_once(self):
        """Alan holds B in two tiers. Two of his tiers is one of him."""
        legs = pr._fixture_options(by_character())[0]["legs"]
        b = next(l for l in legs if l["player"] == "B")
        assert b["backers"] == 1

    def test_leg_probabilities_are_the_house_blend(self):
        legs = pr._fixture_options(by_character())[0]["legs"]
        a = next(l for l in legs if l["player"] == "A")
        # Two characters in the pool: alan's copy of A blends his 0.62 with a
        # 0.57 pack mean. The first copy seen fixes the number.
        assert a["outOf100"] == round((0.62 + 0.57) / 2 * 100)

    def test_the_card_caps_its_legs(self):
        pool = {
            "alan": [slip(9.0, "8/1", [leg(f"P{i}", 1, 0.5) for i in range(8)], 0.01)]
        }
        assert len(pr._fixture_options(pool, limit=5)[0]["legs"]) == 5

    def test_an_empty_pool_offers_nothing_rather_than_a_blank(self):
        assert pr._fixture_options({}) == []

    def test_the_combined_number_is_the_product_of_the_house_legs(self):
        option = pr._fixture_options(by_character())[0]
        product = 1.0
        for l in option["legs"]:
            product *= l["outOf100"] / 100
        assert option["outOf100"] == pytest.approx(round(product * 100), abs=1)
