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


def pool_other_game(n=20):
    out = []
    for i in range(n):
        for line in (0.5, 1.5):
            base = 0.88 - i * 0.02 - (0.3 if line > 1 else 0)
            out.append(
                candidate(
                    f"Q{i}",
                    {c: max(0.05, base + (0.02 if c == "lily" else 0)) for c in FIVE},
                    line=line,
                    fixture="C v D",
                )
            )
    return out


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
    """Three bets per character PER GAME (docs/38), built only from that
    game's players."""

    def test_every_character_produces_every_slate_for_every_game(self):
        built = league.build_slates(pool() + pool_other_game(), FIVE)
        assert set(built) == {"A v B", "C v D"}
        for game in built:
            for cid in FIVE:
                assert set(built[game][cid]) == {s.key for s in ensemble.SLATES}

    def test_each_slate_has_exactly_the_shape_it_promises(self):
        built = league.build_slates(pool(), FIVE)
        for slate in ensemble.SLATES:
            legs = built["A v B"]["alan"][slate.key]["legs"]
            assert len(legs) == slate.legs
            for line, count in slate.shape:
                assert sum(1 for leg in legs if leg["line"] == line) == count

    def test_a_bet_never_leaves_its_own_game(self):
        built = league.build_slates(pool() + pool_other_game(), FIVE)
        for game in built:
            for cid in FIVE:
                for slate in ensemble.SLATES:
                    for leg in built[game][cid][slate.key]["legs"]:
                        assert leg["fixture"] == game

    def test_a_player_is_never_used_twice_in_one_slate(self):
        built = league.build_slates(pool(), FIVE)
        for cid in FIVE:
            for slate in ensemble.SLATES:
                names = [leg["fullName"] for leg in built["A v B"][cid][slate.key]["legs"]]
                assert len(set(names)) == len(names)

    def test_a_character_that_cannot_fill_a_slate_returns_nothing_for_it(self):
        """Committing to a slate you cannot build is worse than passing."""
        built = league.build_slates([candidate("Solo", {c: 0.8 for c in FIVE})], FIVE)
        assert built["A v B"]["alan"]["six-ones"] is None

    def test_genuine_disagreement_still_separates_the_picks(self):
        """Selection is logic-first for everyone now (docs/38, 2026-08-25), so
        with near-identical beliefs the slates legitimately converge. The
        contest lives where beliefs genuinely differ: a character who truly
        rates a player the pack does not must pick differently."""
        maverick = candidate("Maverick", {c: 0.79 for c in FIVE})
        maverick["probs"]["bdog"] = 0.93
        built = league.build_slates(pool() + [maverick], FIVE)
        bdog = {leg["fullName"] for leg in built["A v B"]["bdog"]["six-ones"]["legs"]}
        tayler = {leg["fullName"] for leg in built["A v B"]["tayler"]["six-ones"]["legs"]}
        assert "Maverick Full" in bdog
        assert bdog != tayler


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

    def test_rounds_are_keyed_by_their_first_kickoff_date(self, tmp_path):
        """Not by the week's Monday. Week keys collided the night a round
        finished on a Monday and the next began that Friday: same week, same
        key, and the new round's picks superseded picks nobody ever re-made."""
        from foulgorithm.store import slates as store

        assert store.round_of("2026-08-24T14:00:00+00:00") == "2026-08-24"
        assert store.round_of("2026-08-22T14:00:00+00:00") == "2026-08-22"
        assert store.round_of("2026-08-28T19:00:00+00:00") == "2026-08-28"

    def test_empty_input_is_safe(self, tmp_path):
        from foulgorithm.store import slates as store

        assert store.append([], tmp_path)["written"] == 0


class TestRoundsStaySeparate:
    """The same character plays the same three shapes every week. Without the
    round in the grouping key, legs from two different weeks pooled into one
    bucket, and three legs settling across two rounds could score as one
    slate nobody ever committed. Found live on 2026-08-24, when last week's
    half-settled slates and this week's fresh ones shared a table."""

    @staticmethod
    def graded(cid, slate, round_key, landed, missed):
        return [
            {"model_id": cid, "extra": {"slate": slate, "round": round_key}, "landed": True}
            for _ in range(landed)
        ] + [
            {"model_id": cid, "extra": {"slate": slate, "round": round_key}, "landed": False}
            for _ in range(missed)
        ]

    def test_two_settled_rounds_are_two_results(self):
        rows = self.graded("alan", "three-twos", "2026-08-28", 3, 0) + self.graded(
            "alan", "three-twos", "2026-09-04", 2, 1
        )
        row = next(r for r in league.table(rows, FIVE, since="2026-08-28") if r["id"] == "alan")
        assert row["played"] == 2
        assert (row["won"], row["drawn"]) == (1, 1)

    def test_partial_legs_from_two_rounds_never_merge_into_one_slate(self):
        rows = self.graded("alan", "three-twos", "2026-08-28", 1, 0) + self.graded(
            "alan", "three-twos", "2026-09-04", 1, 1
        )
        row = next(r for r in league.table(rows, FIVE, since="2026-08-28") if r["id"] == "alan")
        assert row["played"] == 0

    def test_the_season_starts_where_it_says(self):
        """Slates from before the season stay on file and graded, and the
        table does not count them: the league opens with the first round
        committed under the upgraded models, so every entry in it came from
        the same generation of machinery."""
        rows = self.graded("alan", "three-twos", "2026-08-17", 3, 0) + self.graded(
            "alan", "three-twos", "2026-08-28", 2, 1
        )
        row = next(r for r in league.table(rows, FIVE, since="2026-08-28") if r["id"] == "alan")
        assert row["played"] == 1
        assert row["drawn"] == 1
        assert row["won"] == 0


class TestBindingVersions:
    """Slates version at lineup time rather than mutate. The one that counts
    is the last committed before the round's first kickoff: after that,
    results are arriving and a replacement would be cherry-picking."""

    @staticmethod
    def slate(published, keys, first_kickoff="2026-08-24T19:00:00+00:00"):
        return {
            "key": "2026-08-24|alan|three-twos",
            "published_at": published,
            "round": "2026-08-24",
            "character": "alan",
            "slate": "three-twos",
            "claim_keys": keys,
            "first_kickoff": first_kickoff,
        }

    def test_the_lineup_time_version_supersedes_the_early_one(self):
        committed = [
            self.slate("2026-08-23T18:00:00+00:00", ["early1", "early2"]),
            self.slate("2026-08-24T18:05:00+00:00", ["late1", "late2"]),
        ]
        binding = league.binding_versions(committed)
        assert len(binding) == 1
        assert binding[0]["claim_keys"] == ["late1", "late2"]

    def test_a_version_published_after_kickoff_is_ignored(self):
        committed = [
            self.slate("2026-08-23T18:00:00+00:00", ["early1"]),
            self.slate("2026-08-24T21:00:00+00:00", ["cheeky1"]),
        ]
        binding = league.binding_versions(committed)
        assert binding[0]["claim_keys"] == ["early1"]

    def test_rows_from_before_the_field_existed_stay_eligible(self):
        old = self.slate("2026-08-17T18:00:00+00:00", ["old1"])
        del old["first_kickoff"]
        old["key"] = "2026-08-17|alan|three-twos"
        assert league.binding_versions([old]) == [old]

    def test_a_new_round_filed_under_the_same_key_does_not_supersede(self):
        """The 24 Aug incident: a round ended on a Monday night and the next
        was published two hours later under the same week key. The new round
        must not replace picks that were never re-made; each round binds its
        own last pre-kickoff version."""
        tonight = self.slate("2026-08-24T17:19:00+00:00", ["tonight1"])
        next_round = self.slate(
            "2026-08-24T19:51:00+00:00",
            ["next1"],
            first_kickoff="2026-08-28T19:00:00+00:00",
        )
        binding = league.binding_versions([tonight, next_round])
        assert len(binding) == 2
        assert {tuple(b["claim_keys"]) for b in binding} == {("tonight1",), ("next1",)}

    def test_the_stored_round_label_is_ignored_when_the_kickoff_is_known(self):
        """One publish filed four characters under one week label and the
        fifth under another. Same first kickoff means same round, whatever
        the label says, so the later version supersedes across labels."""
        a = self.slate(
            "2026-08-24T19:51:00+00:00", ["a1"],
            first_kickoff="2026-08-28T19:00:00+00:00",
        )
        b = dict(
            self.slate(
                "2026-08-24T19:52:00+00:00", ["b1"],
                first_kickoff="2026-08-28T19:00:00+00:00",
            ),
            key="2026-08-31|alan|three-twos",
            round="2026-08-31",
        )
        binding = league.binding_versions([a, b])
        assert len(binding) == 1
        assert binding[0]["claim_keys"] == ["b1"]

    def test_the_joined_round_is_the_kickoff_date_not_the_filed_label(self):
        committed = [
            self.slate(
                "2026-08-24T19:51:00+00:00", ["k1"],
                first_kickoff="2026-08-28T19:00:00+00:00",
            )
        ]
        joined = league.join_slates([{"key": "k1", "won": True}], committed)
        assert joined[0]["extra"]["round"] == "2026-08-28"

    def test_only_the_binding_versions_legs_reach_the_join(self):
        committed = [
            self.slate("2026-08-23T18:00:00+00:00", ["early1"]),
            self.slate("2026-08-24T18:05:00+00:00", ["late1"]),
        ]
        graded = [
            {"key": "early1", "won": True},
            {"key": "late1", "won": False},
        ]
        joined = league.join_slates(graded, committed)
        assert len(joined) == 1
        assert joined[0]["key"] == "late1"
        assert joined[0]["extra"]["round"] == "2026-08-24"


class TestRoundsAreGameweeks:
    """A round is the league's gameweek, and a bet's identity never depends
    on WHEN it was published. Before this, a Saturday republish computed a
    fresh first-kickoff date and the same game's bet landed under a second
    round key: two binding versions of one bet, scored twice. Binding now
    groups per game, so republishing mid-gameweek updates the bet instead
    of duplicating it."""

    @staticmethod
    def slate(published, keys, fixture="C v D", round_key="2026-08-28",
              kickoff="2026-08-30T15:00:00+00:00", matchweek=None):
        return {
            "key": f"{round_key}|alan|three-twos|{fixture}",
            "published_at": published,
            "round": round_key,
            "character": "alan",
            "slate": "three-twos",
            "fixture": fixture,
            "kickoff": kickoff,
            "first_kickoff": "2026-08-28T19:00:00+00:00",
            "claim_keys": keys,
            "matchweek": matchweek,
        }

    def test_a_mid_gameweek_republish_updates_the_bet_never_duplicates_it(self):
        friday = self.slate("2026-08-28T17:00:00+00:00", ["fri1"], round_key="2026-08-28")
        saturday = self.slate("2026-08-29T13:00:00+00:00", ["sat1"], round_key="2026-08-29")
        saturday["first_kickoff"] = "2026-08-29T14:00:00+00:00"
        binding = league.binding_versions([friday, saturday])
        assert len(binding) == 1
        assert binding[0]["claim_keys"] == ["sat1"]

    def test_matchweek_rows_carry_a_gameweek_round_id(self):
        row = self.slate("2026-08-28T17:00:00+00:00", ["k"], matchweek=2)
        assert league.round_id(row) == "mw02"

    def test_the_season_filter_excludes_legacy_dates_and_keeps_gameweeks(self):
        assert league.round_before("2026-08-17", "2026-08-28") is True
        assert league.round_before("2026-08-28", "2026-08-28") is False
        assert league.round_before("mw02", "2026-08-28") is False
        assert league.round_before("mw38", "2026-08-28") is False


class TestFoulDifference:
    """The difference column carries the size of a miss. A 2+ shout where he
    never fouled counts -2; missed by one counts -1; a landed leg +1. A near
    miss and a nowhere miss stop looking the same."""

    @staticmethod
    def leg(landed, deficit=0):
        return {
            "model_id": "alan",
            "extra": {"slate": "three-twos", "round": "2026-08-28"},
            "landed": landed,
            "deficit": deficit,
        }

    def test_a_two_plus_miss_by_two_costs_two(self):
        rows = [self.leg(True), self.leg(False, 2), self.leg(False, 1)]
        row = next(r for r in league.table(rows, FIVE) if r["id"] == "alan")
        assert row["difference"] == 1 - 2 - 1
        assert row["lost"] == 1

    def test_the_join_computes_the_deficit_from_the_graded_counts(self):
        committed = [{
            "key": "2026-08-24|alan|three-twos", "published_at": "a",
            "round": "2026-08-24", "character": "alan", "slate": "three-twos",
            "claim_keys": ["k1", "k2"],
        }]
        graded = [
            {"key": "k1", "won": False, "line": 1.5, "observed": 0.0},
            {"key": "k2", "won": False, "line": 1.5, "observed": 1.0},
        ]
        joined = league.join_slates(graded, committed)
        assert [r["deficit"] for r in joined] == [2, 1]

    def test_a_graded_row_without_counts_falls_back_to_one(self):
        committed = [{
            "key": "2026-08-24|alan|three-twos", "published_at": "a",
            "round": "2026-08-24", "character": "alan", "slate": "three-twos",
            "claim_keys": ["k1"],
        }]
        joined = league.join_slates([{"key": "k1", "won": False}], committed)
        assert joined[0]["deficit"] == 1

    def test_the_result_is_still_decided_by_leg_count_not_deficit(self):
        """A heavy miss costs difference, never extra losses: one missed leg
        of three is still a draw however far it missed by."""
        rows = [self.leg(True), self.leg(True), self.leg(False, 2)]
        row = next(r for r in league.table(rows, FIVE) if r["id"] == "alan")
        assert row["drawn"] == 1
        assert row["difference"] == 0
