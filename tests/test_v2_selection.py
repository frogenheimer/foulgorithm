"""Every competitor bets logic-first; temperament lives inside a named band.

The original five picked on pure temperament, and it made them rogue: a
personality could veto arithmetic, and B-Dog was structurally punished for
his own best numbers. Oliver's call, 2026-08-25: selection unifies across
all eleven. Preference is the character's own probability plus a
temperament term clamped to that character's sway, so an obvious pick is
picked by everyone, the personalities still separate inside the band, and
every slip set carries at least one genuine hot take. Sway widths are the
personality now: Tayler's band is tight, B-Dog's is the widest. The
generations differ by ENGINE, not by selection rules.
"""

import pytest

from foulgorithm.publish import league
from foulgorithm.publish.player_round import (
    CHARACTER_SWAY,
    HOT_TAKE_MARGIN,
    _preference,
)

FIELD = [
    "alan", "lily", "valentina", "tayler", "bdog",
    "pax", "justine", "mabel", "dottie", "dele", "ian",
]


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


class TestBoundedForEveryone:
    def test_every_sway_is_named_and_every_character_has_one(self):
        assert set(CHARACTER_SWAY) == set(FIELD)
        assert all(0 <= s <= 0.15 for s in CHARACTER_SWAY.values())

    @pytest.mark.parametrize("cid", FIELD)
    def test_no_temperament_can_veto_an_obvious_pick(self, cid):
        """Clear of both bands on raw probability beats any personality."""
        obvious = candidate("Obvious", 0.9, 0.9, cid=cid, matches=40.0)
        exciting = candidate("Exciting", 0.55, 0.40, cid=cid, matches=2.0, rate=3.0)
        assert _preference(cid, obvious) > _preference(cid, exciting)

    @pytest.mark.parametrize("cid", FIELD)
    def test_the_sway_is_actually_bounded(self, cid):
        row = candidate("X", 0.5, 0.1, cid=cid, rate=3.0, matches=1.0)
        assert abs(_preference(cid, row) - 0.5) <= CHARACTER_SWAY[cid] + 1e-9

    def test_the_bands_are_the_personality_now(self):
        """The same disagreement moves B-Dog further than it can move Tayler."""
        row = candidate("X", 0.60, 0.45, cid="bdog")
        row["probs"]["tayler"] = 0.60
        bdog_lift = _preference("bdog", row) - 0.60
        tayler_shift = abs(_preference("tayler", row) - 0.60)
        assert bdog_lift > tayler_shift
        assert bdog_lift > CHARACTER_SWAY["tayler"]

    def test_the_five_still_disagree_inside_the_band(self):
        """Two candidates two points apart: Alan chases the recent rate,
        Tayler takes the consensus record."""
        steady = candidate("Steady", 0.62, 0.62, matches=40.0, rate=0.9)
        spiky = candidate("Spiky", 0.60, 0.52, cid="alan", matches=6.0, rate=2.6)
        spiky["probs"]["tayler"] = 0.60
        assert _preference("alan", spiky) > _preference("alan", steady)
        assert _preference("tayler", steady) > _preference("tayler", spiky)


def pool_all_consensus_plus_one_maverick(cid):
    pool = [candidate(f"C{i}", 0.85 - i * 0.01, 0.85 - i * 0.01, cid=cid) for i in range(7)]
    pool += [candidate(f"T{i}", 0.55 - i * 0.01, 0.55 - i * 0.01, cid=cid, line=1.5) for i in range(4)]
    pool.append(candidate("Maverick", 0.55, 0.55 - HOT_TAKE_MARGIN - 0.04, cid=cid))
    return pool


class TestTheHotTakeFloorIsUniversal:
    @pytest.mark.parametrize("cid", ["tayler", "dottie", "alan"])
    def test_an_all_consensus_draft_gets_the_maverick_swapped_in(self, cid):
        built = league.build_slates(pool_all_consensus_plus_one_maverick(cid), FIELD)
        legs = built["A v B"][cid]["six-ones"]["legs"]
        assert "Maverick" in [l["player"] for l in legs]
        assert len(legs) == 6
        assert len({l["fullName"] for l in legs}) == 6

    def test_a_draft_already_carrying_hot_takes_is_untouched(self):
        """The rule is a floor, not a cap: they can have more if they want."""
        pool = [
            candidate(f"H{i}", 0.80 - i * 0.01, 0.60, cid="dottie") for i in range(7)
        ] + [candidate(f"T{i}", 0.55, 0.55, cid="dottie", line=1.5) for i in range(4)]
        built = league.build_slates(pool, FIELD)
        legs = built["A v B"]["dottie"]["six-ones"]["legs"]
        assert len([l for l in legs if l.get("hotTake")]) == 6

    def test_hot_takes_are_flagged_for_every_generation(self):
        built = league.build_slates(pool_all_consensus_plus_one_maverick("tayler"), FIELD)
        legs = built["A v B"]["tayler"]["six-ones"]["legs"]
        maverick = next(l for l in legs if l["player"] == "Maverick")
        assert maverick["hotTake"] is True


class TestJustine:
    def test_justine_covets_the_leaders_number(self):
        row = candidate("X", 0.50, 0.50, cid="justine")
        row["probs"]["alan"] = 0.70
        with_leader = _preference("justine", row, context={"leader": "alan"})
        without = _preference("justine", row, context=None)
        assert with_leader > without
