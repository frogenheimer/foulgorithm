"""Generation 2 bets under bounded rules: logic first, personality in the
band, one hot take guaranteed.

The five pick on pure temperament and that is their charm and their flaw: a
personality could veto arithmetic. The challengers cannot. Their preference
is their own probability plus a temperament term clamped to a named cap, so
an obvious pick is picked by everyone; inside the band the personalities
still separate; and every slip set must carry at least one leg where the
character genuinely parts company with the pack, swapped in only when the
draft came out all-consensus. More hot takes than one are welcome and never
touched: the rule is a floor, not a cap.
"""

import pytest

from foulgorithm.publish import league
from foulgorithm.publish.player_round import (
    HOT_TAKE_MARGIN,
    TEMPERAMENT_SWAY,
    _preference,
)

V2 = ["pax", "justine", "mabel", "dottie", "dele", "ian"]
FIELD = ["alan", "lily", "valentina", "tayler", "bdog"] + V2


def candidate(player, own, pack, cid="dottie", line=0.5, matches=30.0, rate=1.2):
    """One candidate leg where `cid` believes `own` and the rest sit at `pack`."""
    probs = {c: pack for c in FIELD}
    probs[cid] = own
    return {
        "player": player,
        "fullName": f"{player} Full",
        "team": "A",
        "fixture": "A v B",
        "kickoff": "2026-08-28T19:00:00+00:00",
        "market": "committed",
        "line": line,
        "probs": probs,
        "whys": {
            c: {
                "ratePer90": rate,
                "expectedMinutes": 85.0,
                "expected_fouls": 1.1,
                "opponentFactor": 1.05,
                "headToHeadFactor": 1.0,
                "refereeFactor": 1.0,
                "effectiveMatches": matches,
                "startProbability": 1.0,
                "minutesIfStarting": 85.0,
            }
            for c in FIELD
        },
        "thin": False,
    }


class TestBoundedTemperament:
    def test_an_obvious_pick_outranks_any_temperament(self):
        """More than two caps clear on raw probability cannot be vetoed."""
        obvious = candidate("Obvious", 0.9, 0.9, cid="mabel", matches=40.0)
        exciting = candidate("Exciting", 0.7, 0.5, cid="mabel", matches=2.0)
        for cid in V2:
            assert _preference(cid, obvious) > _preference(cid, exciting)

    def test_the_band_still_separates_the_personalities(self):
        """Two points apart: Mabel wants the chaos, Pax wants the record."""
        solid = candidate("Solid", 0.62, 0.62, matches=40.0)
        chaos = candidate("Chaos", 0.60, 0.48, cid="mabel", matches=3.0)
        chaos["probs"]["pax"] = 0.60
        assert _preference("mabel", chaos) > _preference("mabel", solid)
        assert _preference("pax", solid) > _preference("pax", chaos)

    def test_the_sway_is_actually_bounded(self):
        row = candidate("X", 0.5, 0.1, cid="dottie")
        assert abs(_preference("dottie", row) - 0.5) <= TEMPERAMENT_SWAY + 1e-9

    def test_justine_covets_the_leaders_number(self):
        row = candidate("X", 0.50, 0.50, cid="justine")
        row["probs"]["alan"] = 0.70
        with_leader = _preference("justine", row, context={"leader": "alan"})
        without = _preference("justine", row, context=None)
        assert with_leader > without

    def test_ian_is_pure_belief(self):
        row = candidate("X", 0.55, 0.30, cid="ian")
        assert _preference("ian", row) == pytest.approx(0.55)


def pool_all_consensus_plus_one_maverick(cid="dottie"):
    """Seven agreed strong picks a v2 draft would take, and one genuine
    disagreement ranking below them."""
    pool = [candidate(f"C{i}", 0.85 - i * 0.01, 0.85 - i * 0.01, cid=cid) for i in range(7)]
    pool += [candidate(f"T{i}", 0.55 - i * 0.01, 0.55 - i * 0.01, cid=cid, line=1.5) for i in range(4)]
    pool.append(candidate("Maverick", 0.55, 0.55 - HOT_TAKE_MARGIN - 0.04, cid=cid))
    return pool


class TestTheHotTakeFloor:
    def test_an_all_consensus_draft_gets_the_maverick_swapped_in(self):
        built = league.build_slates(pool_all_consensus_plus_one_maverick(), FIELD)
        legs = built["A v B"]["dottie"]["six-ones"]["legs"]
        assert "Maverick" in [l["player"] for l in legs]
        assert len(legs) == 6
        assert len({l["fullName"] for l in legs}) == 6

    def test_a_generation_one_character_is_never_forced(self):
        built = league.build_slates(pool_all_consensus_plus_one_maverick("tayler"), FIELD)
        legs = built["A v B"]["tayler"]["six-ones"]["legs"]
        assert "Maverick" not in [l["player"] for l in legs]

    def test_a_draft_already_carrying_hot_takes_is_untouched(self):
        """The rule is a floor, not a cap: they can have more if they want."""
        pool = [
            candidate(f"H{i}", 0.80 - i * 0.01, 0.60, cid="dottie") for i in range(7)
        ] + [candidate(f"T{i}", 0.55, 0.55, cid="dottie", line=1.5) for i in range(4)]
        built = league.build_slates(pool, FIELD)
        legs = built["A v B"]["dottie"]["six-ones"]["legs"]
        hot = [l for l in legs if l.get("hotTake")]
        assert len(hot) == 6  # every leg is a genuine disagreement, all kept

    def test_hot_takes_are_flagged_on_the_legs(self):
        built = league.build_slates(pool_all_consensus_plus_one_maverick(), FIELD)
        legs = built["A v B"]["dottie"]["six-ones"]["legs"]
        maverick = next(l for l in legs if l["player"] == "Maverick")
        assert maverick["hotTake"] is True
