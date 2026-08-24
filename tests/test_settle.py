"""Settlement closes the loop, and the loop is the whole credibility of this.

Publishing predictions without grading them is what a tipster account does. The
grading job has existed since the start; nothing built the outcomes it needs.

The route is not obvious. The league's API gives per-fixture stats at TEAM level
and per-player stats only as season totals, so a player's fouls in one match are
recoverable as the difference between two weekly snapshots and not otherwise.

That difference is only safe when the player made exactly one appearance between
snapshots. Two appearances and the difference is a sum, which cannot be split.
Those are left ungraded, deliberately.
"""

import pytest

from foulgorithm.jobs import settle


def _snap(**players):
    return {name: {"fouls": f, "was_fouled": w, "appearances": a}
            for name, (f, w, a) in players.items()}


class TestDiff:
    def test_one_appearance_gives_that_match(self):
        before = _snap(alice=(4, 2, 3))
        after = _snap(alice=(6, 3, 4))
        out = settle.per_match(before, after)
        assert out["alice"]["fouls_committed"] == 2
        assert out["alice"]["fouls_drawn"] == 1

    def test_two_appearances_are_not_split(self):
        # A midweek round. The sum is known and the parts are not, so guessing
        # here would put invented numbers into a public track record.
        before = _snap(bob=(4, 2, 3))
        after = _snap(bob=(9, 5, 5))
        assert "bob" not in settle.per_match(before, after)

    def test_a_player_who_did_not_feature_is_absent(self):
        before = _snap(carol=(4, 2, 3))
        after = _snap(carol=(4, 2, 3))
        assert "carol" not in settle.per_match(before, after)

    def test_a_debutant_is_graded_from_nothing(self):
        # Absent from the earlier snapshot means zero, not unknown. The ranked
        # endpoint omits anyone on zero rather than listing them.
        after = _snap(dave=(2, 1, 1))
        assert settle.per_match({}, after)["dave"]["fouls_committed"] == 2

    def test_a_negative_difference_is_refused(self):
        # Totals only ever rise. A fall means the season rolled over or the
        # source changed shape, and settling against it would be nonsense.
        before = _snap(erin=(9, 5, 5))
        after = _snap(erin=(2, 1, 1))
        with pytest.raises(ValueError, match="fell"):
            settle.per_match(before, after)


class TestOutcomes:
    def test_outcomes_are_keyed_for_the_grader(self):
        out = settle.outcomes(settle.per_match({}, _snap(alice=(3, 1, 1))))
        assert out[("alice", "player_fouls_committed")] == 3
        assert out[("alice", "player_fouls_drawn")] == 1


class TestWaitingForTheStatsToPost:
    """Three fixtures graded near zero, all from the same 14:00 slot, and the
    five Ipswich players captured all showed exactly zero fouls in a 26-foul
    match. That is not a quiet afternoon, it is a stat that had not posted.

    The damage is done by TAKING the snapshot, not by reading it: a half-posted
    reading becomes the next run's baseline, so the fouls that post an hour
    later arrive in a window where appearances did not move, and the
    exactly-one-appearance rule then discards them for ever. So the run has to
    defer whole rather than settle what it can.
    """

    def fixture(self, hours_ago, complete=True):
        from datetime import datetime, timedelta, timezone

        class F:
            kickoff_utc = datetime.now(timezone.utc) - timedelta(hours=hours_ago)

        F.complete = complete
        return F()

    def test_a_match_that_finished_long_ago_is_ready(self):
        assert settle.pending_fixtures([self.fixture(hours_ago=40)]) == []

    def test_a_match_that_kicked_off_an_hour_ago_is_not(self):
        pending = settle.pending_fixtures([self.fixture(hours_ago=1, complete=False)])
        assert len(pending) == 1

    def test_a_match_just_inside_the_delay_is_still_pending(self):
        """STATS_DELAY is three hours and described as conservative. Just
        inside it counts as pending, because the cost of waiting one run is a
        delay and the cost of not waiting is data destroyed permanently."""
        assert len(settle.pending_fixtures([self.fixture(hours_ago=2.5)])) == 1

    def test_a_match_that_has_not_kicked_off_is_not_pending(self):
        assert settle.pending_fixtures([self.fixture(hours_ago=-24, complete=False)]) == []

    def test_one_fresh_fixture_holds_the_whole_run(self):
        """Settling the ready ones and snapshotting anyway would freeze the
        fresh one's half-posted state into the baseline, which is the bug."""
        fixtures = [self.fixture(hours_ago=40), self.fixture(hours_ago=1, complete=False)]
        assert len(settle.pending_fixtures(fixtures)) == 1
