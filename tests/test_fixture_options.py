"""The fixture card shows the crossover of the committed slates.

Oliver's call, 2026-08-24, in two steps: first that the card carries the
picks the five most agree on rather than one temperament's reach, then that
agreement means the committed slates, the same picks the matrix shows and
the league table scores, not the display-only tier ladders. These tests pin
the counting rules that make "4 of 5 back this" mean what it says: a
character backs a leg once however many of his three shapes repeat it,
ranking is backers first and house blend second, the blend is the unweighted
mean of every character's number from the candidate table, and each fixture
gets its own card built only from its own legs.
"""

import pytest

from foulgorithm.publish import player_round as pr

GAME = "Arsenal v Coventry"
OTHER = "Palace v Wolves"


def cand(player, fouls, probs, fixture=GAME, market="committed"):
    return {
        "player": player,
        "fullName": f"{player} F",
        "team": "T",
        "fixture": fixture,
        "kickoff": "2026-08-28T19:00:00+00:00",
        "market": market,
        "line": fouls - 0.5,
        "probs": probs,
        "thin": False,
    }


def leg(player, fouls, prob, fixture=GAME, market="committed"):
    return {
        "player": player,
        "fullName": f"{player} F",
        "team": "T",
        "fixture": fixture,
        "kickoff": "2026-08-28T19:00:00+00:00",
        "market": market,
        "line": fouls - 0.5,
        "fouls": fouls,
        "prob": prob,
        "outOf100": round(prob * 100),
        "thin": False,
    }


def shapes(**built):
    """Slate shapes for one character: shapes(six_ones=[...]) with None for a pass."""
    return {
        key.replace("_", "-"): ({"legs": legs, "label": key} if legs is not None else None)
        for key, legs in built.items()
    }


CANDIDATES = [
    cand("A", 1, {"alan": 0.62, "bdog": 0.58}),
    cand("B", 2, {"alan": 0.40, "bdog": 0.30}),
    cand("C", 2, {"alan": 0.35, "bdog": 0.37}),
    cand("D", 1, {"alan": 0.44, "bdog": 0.50}),
]


def slates():
    """Two characters. A is backed by both; B only by alan, and in two of
    alan's shapes, which must still count him once."""
    return {
        "alan": shapes(
            six_ones=[leg("A", 1, 0.62), leg("B", 2, 0.40)],
            two_and_two=[leg("B", 2, 0.40), leg("C", 2, 0.35)],
        ),
        "bdog": shapes(six_ones=[leg("A", 1, 0.58), leg("D", 1, 0.50)]),
    }


class TestTheCrossover:
    def test_one_card_per_fixture_never_a_specific_character(self):
        options = pr._fixture_options(slates(), CANDIDATES)
        assert list(options) == [GAME]
        assert len(options[GAME]) == 1
        assert options[GAME][0]["character"] == "consensus"
        assert options[GAME][0]["characterName"] == "The five"

    def test_legs_rank_by_backers_then_house(self):
        legs = pr._fixture_options(slates(), CANDIDATES)[GAME][0]["legs"]
        assert legs[0]["player"] == "A"
        assert legs[0]["backers"] == 2
        assert [l["backers"] for l in legs] == sorted(
            [l["backers"] for l in legs], reverse=True
        )

    def test_a_character_repeating_a_leg_across_shapes_backs_it_once(self):
        """Alan holds B in two shapes. Two of his shapes is one of him."""
        legs = pr._fixture_options(slates(), CANDIDATES)[GAME][0]["legs"]
        b = next(l for l in legs if l["player"] == "B")
        assert b["backers"] == 1

    def test_leg_probabilities_are_the_house_blend(self):
        """A's number is the mean of every character's, not any one copy."""
        legs = pr._fixture_options(slates(), CANDIDATES)[GAME][0]["legs"]
        a = next(l for l in legs if l["player"] == "A")
        assert a["outOf100"] == round((0.62 + 0.58) / 2 * 100)

    def test_the_card_caps_its_legs(self):
        pool = {"alan": shapes(six_ones=[leg(f"P{i}", 1, 0.5) for i in range(8)])}
        cands = [cand(f"P{i}", 1, {"alan": 0.5}) for i in range(8)]
        assert len(pr._fixture_options(pool, cands, limit=5)[GAME][0]["legs"]) == 5

    def test_empty_slates_offer_nothing_rather_than_a_blank(self):
        assert pr._fixture_options({}, CANDIDATES) == {}

    def test_a_passed_shape_is_skipped_not_crashed_on(self):
        assert pr._fixture_options({"alan": shapes(six_ones=None)}, CANDIDATES) == {}

    def test_the_combined_number_is_the_product_of_the_house_legs(self):
        option = pr._fixture_options(slates(), CANDIDATES)[GAME][0]
        product = 1.0
        for l in option["legs"]:
            product *= l["outOf100"] / 100
        assert option["outOf100"] == pytest.approx(round(product * 100), abs=1)

    def test_each_fixture_card_holds_only_its_own_legs(self):
        pool = {
            "alan": shapes(
                six_ones=[leg("A", 1, 0.62), leg("X", 1, 0.55, fixture=OTHER)]
            )
        }
        cands = CANDIDATES + [cand("X", 1, {"alan": 0.55, "bdog": 0.45}, fixture=OTHER)]
        options = pr._fixture_options(pool, cands)
        assert set(options) == {GAME, OTHER}
        assert [l["player"] for l in options[GAME][0]["legs"]] == ["A"]
        assert [l["player"] for l in options[OTHER][0]["legs"]] == ["X"]
