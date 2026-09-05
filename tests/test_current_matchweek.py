"""The homepage opens on the matchweek the site is actually publishing for.

`currentMatchweek` used to be the highest week with a COMPLETED game, so it
named the round that had just finished rather than the one being played. On
the Tuesday to Friday of a matchweek the homepage opened on last week, whose
games were all over, while the picks on the board were for the round coming.
"""

from foulgorithm.publish import season


def _fx(week, status):
    return {"matchweek": week, "status": status}


def test_the_round_being_played_is_current():
    fixtures = [_fx(1, "C"), _fx(2, "C"), _fx(3, "C"), _fx(3, "U"), _fx(4, "U")]
    assert season.current_matchweek(fixtures) == 3


def test_a_round_not_started_is_current_once_the_last_one_is_over():
    """Tuesday of a new week: nothing in week 3 has been played, and week 3
    is what the board carries picks for."""
    fixtures = [_fx(1, "C"), _fx(2, "C"), _fx(3, "U"), _fx(3, "U")]
    assert season.current_matchweek(fixtures) == 3


def test_the_opening_week_is_current_before_a_ball_is_kicked():
    assert season.current_matchweek([_fx(1, "U"), _fx(2, "U")]) == 1


def test_the_last_week_holds_once_the_season_is_over():
    fixtures = [_fx(37, "C"), _fx(38, "C")]
    assert season.current_matchweek(fixtures) == 38


def test_fixtures_without_a_matchweek_are_ignored():
    fixtures = [_fx(None, "U"), _fx(2, "C"), _fx(3, "U")]
    assert season.current_matchweek(fixtures) == 3


def test_no_fixtures_is_week_one():
    assert season.current_matchweek([]) == 1
