"""The five, scored on identical bets, read as a football table.

Comparing characters is only fair when they are asked the same question. Left to
choose their own shapes, a cautious one looks good by picking near-certainties
and a bold one looks bad by reaching, and the table measures difficulty rather
than judgement. So every gameweek each of them commits to the same three slates
and the only thing that varies is WHICH players they pick.
"""

import pytest

from foulgorithm.models import ensemble
from foulgorithm.publish import league


def candidate(player, cid_probs, market="committed", line=0.5, fixture="A v B"):
    return {
        "player": player,
        "fullName": f"{player} Full",
        "team": "A",
        "fixture": fixture,
        "kickoff": "2026-08-24T14:00:00+00:00",
        "market": market,
        "line": line,
        "probs": dict(cid_probs),
        # The real why block, because the preference function reads all of it
        # and a thin fixture only proves the fixture is thin.
        "whys": {
            c: {
                "ratePer90": 1.2,
                "expectedMinutes": 85.0,
                "expected_fouls": 1.1,
                "opponentFactor": 1.05,
                "headToHeadFactor": 1.0,
                "refereeFactor": 1.0,
                "effectiveMatches": 30.0,
                "startProbability": 1.0,
                "minutesIfStarting": 85.0,
            }
            for c in cid_probs
        },
        "thin": False,
    }


FIVE = ["alan", "lily", "valentina", "tayler", "bdog"]


def pool(n=20):
    """Enough candidates at both lines for every slate to be fillable."""
    out = []
    for i in range(n):
        for line in (0.5, 1.5):
            base = 0.9 - i * 0.02 - (0.3 if line > 1 else 0)
            out.append(
                candidate(
                    f"P{i}",
                    {c: max(0.05, base + (0.02 if c == "alan" else 0)) for c in FIVE},
                    line=line,
                )
            )
    return out


class TestBuildingSlates:
    def test_every_character_produces_every_slate(self):
        built = league.build_slates(pool(), FIVE)
        for cid in FIVE:
            assert set(built[cid]) == {s.key for s in ensemble.SLATES}

    def test_each_slate_has_exactly_the_shape_it_promises(self):
        built = league.build_slates(pool(), FIVE)
        for slate in ensemble.SLATES:
            legs = built["alan"][slate.key]["legs"]
            assert len(legs) == slate.legs
            for line, count in slate.shape:
                assert sum(1 for leg in legs if leg["line"] == line) == count

    def test_a_player_is_never_used_twice_in_one_slate(self):
        built = league.build_slates(pool(), FIVE)
        for cid in FIVE:
            for slate in ensemble.SLATES:
                names = [leg["fullName"] for leg in built[cid][slate.key]["legs"]]
                assert len(set(names)) == len(names)

    def test_a_character_that_cannot_fill_a_slate_returns_nothing_for_it(self):
        """Committing to a slate you cannot build is worse than passing."""
        built = league.build_slates([candidate("Solo", {c: 0.8 for c in FIVE})], FIVE)
        assert built["alan"]["six-ones"] is None

    def test_the_five_do_not_all_pick_the_same_players(self):
        built = league.build_slates(pool(), FIVE)
        picked = {
            cid: tuple(leg["fullName"] for leg in built[cid]["six-ones"]["legs"])
            for cid in FIVE
        }
        assert len(set(picked.values())) > 1, "if they agree entirely there is no contest"


class TestTheHouseNumber:
    def test_it_is_the_average_of_the_five(self):
        row = candidate("X", {"alan": 0.6, "lily": 0.7, "valentina": 0.5, "tayler": 0.4, "bdog": 0.8})
        assert league.house_probability(row, FIVE) == pytest.approx(0.6)

    def test_it_refuses_to_invent_a_number_when_nobody_has_one(self):
        with pytest.raises(ValueError):
            league.house_probability(candidate("X", {}), FIVE)


class TestTheTable:
    @staticmethod
    def graded(cid, slate, landed, missed):
        return [
            {"model_id": cid, "extra": {"slate": slate}, "landed": True}
            for _ in range(landed)
        ] + [
            {"model_id": cid, "extra": {"slate": slate}, "landed": False}
            for _ in range(missed)
        ]

    def test_a_full_slate_is_a_win(self):
        table = league.table(self.graded("alan", "three-twos", 3, 0), FIVE)
        row = next(r for r in table if r["id"] == "alan")
        assert (row["won"], row["points"], row["difference"]) == (1, 3, 3)

    def test_one_leg_short_is_a_draw_not_a_wipeout(self):
        table = league.table(self.graded("alan", "three-twos", 2, 1), FIVE)
        row = next(r for r in table if r["id"] == "alan")
        assert (row["drawn"], row["points"]) == (1, 1)
        assert row["difference"] == 1

    def test_two_short_is_a_loss(self):
        table = league.table(self.graded("alan", "three-twos", 1, 2), FIVE)
        row = next(r for r in table if r["id"] == "alan")
        assert (row["lost"], row["points"], row["difference"]) == (1, 0, -1)

    def test_it_sorts_on_points_then_difference(self):
        rows = (
            self.graded("alan", "three-twos", 3, 0)
            + self.graded("lily", "three-twos", 2, 1)
            + self.graded("bdog", "six-ones", 6, 0)
            + self.graded("bdog", "three-twos", 3, 0)
        )
        table = league.table(rows, FIVE)
        assert [r["id"] for r in table[:2]] == ["bdog", "alan"]

    def test_every_character_appears_even_with_nothing_graded(self):
        table = league.table([], FIVE)
        assert {r["id"] for r in table} == set(FIVE)
        assert all(r["played"] == 0 for r in table)

    def test_an_ungraded_leg_does_not_count_as_a_miss(self):
        """A slate half settled is not a slate lost."""
        rows = [{"model_id": "alan", "extra": {"slate": "three-twos"}, "landed": True}]
        table = league.table(rows, FIVE)
        assert next(r for r in table if r["id"] == "alan")["played"] == 0


class TestJoiningGradedClaimsToSlates:
    """A slate holds the KEYS of the claims it selected, and grading holds the
    outcomes under the same keys, so the two join on the key.

    Storing membership on the claim itself failed twice, and both failures were
    the append-only rule working: a slate leg collides with the claim already
    there, and a claim recorded on Thursday cannot gain a field on Friday.
    """

    COMMITTED = [
        {
            "character": "alan",
            "slate": "three-twos",
            "claim_keys": ["aaa", "bbb", "ccc"],
        }
    ]

    def test_a_settled_leg_is_attributed_to_its_slate(self):
        graded = [{"key": "aaa", "won": True}]
        joined = league.join_slates(graded, self.COMMITTED)
        assert joined[0]["extra"]["slate"] == "three-twos"
        assert joined[0]["model_id"] == "alan"

    def test_won_becomes_landed(self):
        graded = [{"key": "aaa", "won": False}]
        assert league.join_slates(graded, self.COMMITTED)[0]["landed"] is False

    def test_an_unsettled_leg_is_absent_rather_than_a_miss(self):
        """Half a slate settled is not half a slate lost."""
        graded = [{"key": "aaa", "won": True}]
        joined = league.join_slates(graded, self.COMMITTED)
        assert len(joined) == 1
        assert league.table(joined, FIVE)[0]["played"] == 0

    def test_a_fully_settled_slate_scores(self):
        graded = [{"key": k, "won": True} for k in ("aaa", "bbb", "ccc")]
        joined = league.join_slates(graded, self.COMMITTED)
        row = next(r for r in league.table(joined, FIVE) if r["id"] == "alan")
        assert (row["played"], row["points"]) == (1, 3)

    def test_a_claim_no_slate_selected_is_ignored(self):
        graded = [{"key": "zzz", "won": True}]
        assert league.join_slates(graded, self.COMMITTED) == []


class TestTheSlateStore:
    """Committed slates are promises made before kickoff and never revised."""

    def make(self, character="alan", slate="three-twos", keys=("a", "b", "c")):
        from foulgorithm.store import slates as store

        return store.Committed(
            published_at="2026-08-22T10:00:00+00:00",
            round="2026-08-24",
            character=character,
            slate=slate,
            claim_keys=list(keys),
        )

    def test_one_slate_per_character_per_shape_per_round(self):
        from foulgorithm.store import slates as store

        a = self.make()
        b = self.make(keys=("x", "y", "z"))
        assert a.key == b.key
        assert store.Committed(**{**a.__dict__, "character": "lily"}).key != a.key

    def test_a_committed_slate_is_never_replaced(self, tmp_path):
        from foulgorithm.store import slates as store

        store.append([self.make()], tmp_path)
        again = store.append([self.make(keys=("x", "y", "z"))], tmp_path)
        assert again["written"] == 0 and again["skipped"] == 1

        rows = store.load_all(tmp_path)
        assert len(rows) == 1
        assert rows[0]["claim_keys"] == ["a", "b", "c"], "the first promise stands"

    def test_different_shapes_coexist(self, tmp_path):
        from foulgorithm.store import slates as store

        result = store.append(
            [self.make(slate="three-twos"), self.make(slate="six-ones")], tmp_path
        )
        assert result["written"] == 2

    def test_rounds_are_separate_files(self, tmp_path):
        from foulgorithm.store import slates as store

        assert store.round_of("2026-08-24T14:00:00+00:00") == "2026-08-24"
        assert store.round_of("2026-08-22T14:00:00+00:00") == "2026-08-17"

    def test_empty_input_is_safe(self, tmp_path):
        from foulgorithm.store import slates as store

        assert store.append([], tmp_path)["written"] == 0
