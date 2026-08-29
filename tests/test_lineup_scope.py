"""Confirmed lineups counted against the fixtures we are actually predicting.

The feed returns every confirmed eleven it holds, last round's included, and the
site reported that count against the fixtures on the board. Once the board moved
to the round that is coming, it read "18 of 2".

The keys are "Club|Home v Away" composites. Filtering them by club name matched
nothing and produced a confident zero, which is the worse failure of the two: it
is indistinguishable from "no lineups are out yet" and would have stayed zero
through kickoff.
"""

from foulgorithm.publish.player_round import scope_lineups

LINEUPS = {
    "Arsenal|Arsenal v Coventry": ["a"],
    "Coventry|Arsenal v Coventry": ["b"],
    "Fulham|Fulham v Chelsea": ["c"],
    "Chelsea|Fulham v Chelsea": ["d"],
}


class TestScoping:
    def test_it_keeps_the_fixtures_being_predicted(self):
        kept = scope_lineups(LINEUPS, {"Fulham v Chelsea"})
        assert set(kept) == {"Fulham|Fulham v Chelsea", "Chelsea|Fulham v Chelsea"}

    def test_it_drops_last_round(self):
        kept = scope_lineups(LINEUPS, {"Fulham v Chelsea"})
        assert not any("Coventry" in k for k in kept)

    def test_it_matches_on_the_fixture_not_the_club(self):
        """The regression: club names never appear alone in these keys."""
        assert scope_lineups(LINEUPS, {"Fulham", "Chelsea"}) == {}

    def test_no_fixtures_keeps_everything(self):
        """Nothing to scope to is not the same as nothing matching."""
        assert scope_lineups(LINEUPS, set()) == LINEUPS

    def test_an_empty_feed_is_safe(self):
        assert scope_lineups({}, {"Fulham v Chelsea"}) == {}


class TestTheSheetsVerdictForEveryone:
    """Once a team sheet exists, every player carries its verdict: the eleven
    start, the named substitutes are on the bench, and everyone else is out.
    Sending only "start" left the rest on their season start chance."""

    def test_starters_bench_and_out(self):
        from foulgorithm.publish.player_round import Selection

        assert Selection("A", "A B", None, "MF", True, "", confirmed=True, sheet="start").sheet == "start"
        assert Selection("C", "C D", None, "MF", True, "", sheet="bench").sheet == "bench"
        assert Selection("E", "E F", None, "MF", True, "", sheet="out").sheet == "out"
        assert Selection("G", "G H", None, "MF", True, "").sheet is None
