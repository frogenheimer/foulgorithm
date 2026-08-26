"""Which division a club is in, and what that lets us say about it.

The twenty Premier League clubs carry player-level foul data. The twenty-four
Championship clubs carry none at all: the worldfootballR archive is first tier
only for England, FPL is the Premier League by definition, and the league's own
API does not know the second tier exists. That asymmetry is the whole reason
this module exists, so it is asserted here rather than left as a comment.
"""

import pytest

from foulgorithm.identity import teams


class TestDivisionOf:
    def test_premier_league_clubs_are_e0(self):
        assert teams.division_of("Arsenal") == "E0"
        assert teams.division_of("Nott'm Forest") == "E0"

    def test_championship_clubs_are_e1(self):
        assert teams.division_of("Wrexham") == "E1"
        assert teams.division_of("West Brom") == "E1"

    def test_a_club_in_neither_is_none(self):
        # League One, League Two and non-league. Not an error: a cup draw is
        # allowed to contain clubs we hold nothing for.
        assert teams.division_of("Salford") is None
        assert teams.division_of("Barnsley") is None

    def test_no_club_is_in_both_divisions(self):
        assert not (teams.PREMIER_LEAGUE_CLUBS & teams.CHAMPIONSHIP_CLUBS)

    def test_the_championship_has_twenty_four_clubs(self):
        assert len(teams.CHAMPIONSHIP_CLUBS) == 24

    def test_the_premier_league_has_twenty(self):
        assert len(teams.PREMIER_LEAGUE_CLUBS) == 20


class TestPlayerDataAvailability:
    """The asymmetry, stated as a test so it cannot rot into an assumption."""

    def test_premier_league_clubs_have_player_data(self):
        assert teams.has_player_data("Arsenal") is True

    def test_championship_clubs_do_not(self):
        # features/promotion.py: "Championship player data does not exist at
        # any price." No player pick may ever be published for these clubs.
        assert teams.has_player_data("Wrexham") is False

    def test_an_unknown_club_does_not(self):
        assert teams.has_player_data("Salford") is False


class TestToFixtureName:
    def test_championship_api_football_spellings_resolve(self):
        assert teams.to_fixture_name("Queens Park Rangers") == "QPR"
        assert teams.to_fixture_name("West Bromwich Albion") == "West Brom"
        assert teams.to_fixture_name("Sheffield Wednesday") == "Sheffield Weds"
        assert teams.to_fixture_name("Wolverhampton Wanderers") == "Wolves"

    def test_championship_football_data_spellings_pass_through(self):
        assert teams.to_fixture_name("Wrexham") == "Wrexham"
        assert teams.to_fixture_name("QPR") == "QPR"

    def test_premier_league_resolution_is_unchanged(self):
        assert teams.to_fixture_name("Nottingham Forest") == "Nott'm Forest"
        assert teams.to_fixture_name("Man Utd") == "Man United"

    def test_a_club_outside_both_divisions_is_none(self):
        assert teams.to_fixture_name("Salford City") is None


class TestHoldsData:
    def test_a_tie_between_two_known_clubs_is_playable(self):
        assert teams.holds_data("Arsenal") and teams.holds_data("Wrexham")

    def test_a_tie_with_a_league_one_club_is_not(self):
        assert not teams.holds_data("Salford")
