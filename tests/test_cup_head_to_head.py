"""Past meetings between these two clubs, as a list of facts.

Distinct from features/head_to_head, which computes a shrunk pairing
adjustment for the model. This is the display version: every meeting we hold,
labelled with the division it was played in, so a Championship meeting is not
read as evidence about a Premier League tie.

The pairing effect is real and small, about 5% on a base near 21 fouls, and
three quarters of any observed residual is noise. Nothing here shrinks
anything, because nothing here is a prediction. It is a table of what happened.
"""

from foulgorithm.stats import cup_head_to_head as h2h
from tests.test_team_record import match


def meeting(home, away, hf, af, season, division="E0", date="2026-01-04"):
    m = match(home, away, hf=hf, af=af, season=season, division=division)
    m["kickoff_utc"] = date
    return m


class TestMeetings:
    def test_it_finds_the_pairing_in_both_directions(self):
        rows = [
            meeting("Arsenal", "Burnley", 10, 14, "2025-26"),
            meeting("Burnley", "Arsenal", 13, 9, "2025-26"),
            meeting("Arsenal", "Chelsea", 11, 11, "2025-26"),
        ]
        out = h2h.build("Arsenal", "Burnley", rows)
        assert out.meetings == 2

    def test_each_row_is_told_from_the_home_sides_point_of_view(self):
        rows = [meeting("Burnley", "Arsenal", 13, 9, "2025-26")]
        row = h2h.build("Arsenal", "Burnley", rows).rows[0]
        assert row["home"] == "Burnley"
        assert row["homeFouls"] == 13
        assert row["awayFouls"] == 9

    def test_every_row_names_the_division_it_was_played_in(self):
        # A Championship meeting is not evidence about a Premier League tie,
        # and the reader can only know that if the row says which it was.
        rows = [meeting("Burnley", "Arsenal", 13, 9, "2021-22", division="E1")]
        assert h2h.build("Arsenal", "Burnley", rows).rows[0]["division"] == "Championship"

    def test_meetings_come_back_newest_first(self):
        rows = [
            meeting("Arsenal", "Burnley", 10, 14, "2024-25", date="2025-02-01"),
            meeting("Burnley", "Arsenal", 13, 9, "2025-26", date="2026-02-01"),
        ]
        out = h2h.build("Arsenal", "Burnley", rows)
        assert [r["season"] for r in out.rows] == ["2025-26", "2024-25"]


class TestAverages:
    def test_each_clubs_fouls_in_these_games_are_averaged(self):
        rows = [
            meeting("Arsenal", "Burnley", 10, 14, "2025-26"),
            meeting("Burnley", "Arsenal", 12, 8, "2025-26"),
        ]
        out = h2h.build("Arsenal", "Burnley", rows)
        assert out.fouls["Arsenal"] == 9.0  # 10 at home, 8 away
        assert out.fouls["Burnley"] == 13.0  # 14 away, 12 at home

    def test_the_pairing_total_is_published(self):
        rows = [meeting("Arsenal", "Burnley", 10, 14, "2025-26")]
        assert h2h.build("Arsenal", "Burnley", rows).total_fouls == 24.0


class TestNeverMet:
    def test_two_clubs_who_have_never_met_say_so(self):
        rows = [meeting("Arsenal", "Chelsea", 11, 11, "2025-26")]
        out = h2h.build("Arsenal", "Wrexham", rows)
        assert out.meetings == 0
        assert out.rows == []
        assert out.total_fouls is None
