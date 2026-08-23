"""Player-match files for the other big-five leagues, from the same archive.

We read one of twenty-four `misc` files in a release we already depend on. The
other five carry the same schema for Italy, Spain, Germany, France and the USA,
roughly 370,000 additional player-matches.

**They cannot simply be concatenated.** Serie A runs 1.197 fouls per 90 against
England's 0.972, a 23% gap, while England's own eight-season spread is 9%. The
league effect is more than twice the season effect, so every row has to carry
which league it came from and no caller may forget it.
"""

import pytest

from foulgorithm.sources import leagues


class TestTheCatalogue:
    def test_england_is_there_and_is_what_we_already_read(self):
        assert "ENG" in leagues.LEAGUES
        assert leagues.LEAGUES["ENG"].tier == 1

    def test_the_other_big_five_are_there(self):
        assert {"ESP", "ITA", "GER", "FRA"} <= set(leagues.LEAGUES)

    def test_every_league_has_a_working_url(self):
        for code, league in leagues.LEAGUES.items():
            url = leagues.url_for(code)
            assert url.startswith("https://")
            assert league.file_stem in url

    def test_an_unknown_league_raises_rather_than_guessing(self):
        with pytest.raises(KeyError):
            leagues.url_for("XYZ")


class TestNormalising:
    """FBref's column names become ours, once, here."""

    def raw(self, **kw):
        base = {
            "Player": "Rodrigo Bentancur",
            "Team": "Tottenham",
            "Home_Team": "Brentford",
            "Away_Team": "Tottenham",
            "Match_Date": "2026-08-22",
            "Min": 90,
            "Pos": "MF",
            "Fls": 3,
            "Fld": 1,
            "CrdY": 1,
            "CrdR": 0,
            "TklW": 2,
            "Int": 1,
            "Season_End_Year": 2026,
        }
        base.update(kw)
        return base

    def test_columns_are_renamed_to_ours(self):
        row = leagues.normalise(self.raw(), "ITA")
        assert row["fouls_committed"] == 3
        assert row["fouls_drawn"] == 1
        assert row["minutes"] == 90
        assert row["player"] == "Rodrigo Bentancur"

    def test_every_row_carries_its_league(self):
        """The 23% gap means a row without a league is a row that will mislead."""
        assert leagues.normalise(self.raw(), "ITA")["league"] == "ITA"
        assert leagues.normalise(self.raw(), "ENG")["league"] == "ENG"

    def test_the_opponent_is_derived_from_the_two_clubs(self):
        row = leagues.normalise(self.raw(), "ENG")
        assert row["opponent"] == "Brentford"
        assert row["venue"] == "away"

    def test_a_home_player_gets_the_other_club(self):
        row = leagues.normalise(self.raw(Team="Brentford"), "ENG")
        assert row["opponent"] == "Tottenham"
        assert row["venue"] == "home"

    def test_a_missing_foul_count_stays_missing(self):
        row = leagues.normalise(self.raw(Fls=None), "ENG")
        assert row["fouls_committed"] is None
