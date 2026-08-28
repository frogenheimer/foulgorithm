"""Predict the round that is coming, not the one in whichever file we read.

football-data.co.uk publishes a fixtures file holding the current round, and it
does not roll over to the next one until midweek. On a Sunday evening nine of
its ten fixtures have already kicked off, so every pick was generated for a game
already played, and the homepage rendered those cards as results rather than
picks. Between Sunday night and the rollover the site had no picks at all.

The league's own fixture list knows the whole season, so that decides WHICH
fixtures are next. football-data still supplies the referee and the odds, which
the league's list does not carry, joined on rather than trusted for the dates.
"""

from datetime import datetime, timedelta, timezone

import pytest

from foulgorithm.features import next_round


def at(hours):
    return datetime(2026, 8, 23, 18, 0, tzinfo=timezone.utc) + timedelta(hours=hours)


def fixture(home, away, hours, referee=None):
    return {
        "home_team_raw": home,
        "away_team_raw": away,
        "kickoff_utc": at(hours),
        "referee_raw": referee,
        "odds_home": 2.0,
        "odds_draw": 3.4,
        "odds_home_raw": None,
    }


class Live:
    """Stands in for the league's fixture list."""

    def __init__(self, rows):
        self.rows = rows


def live(home, away, hours):
    return type("F", (), {"home": home, "away": away, "kickoff_utc": at(hours), "status": "U"})()


class TestChoosingTheRound:
    def test_a_kicked_off_fixture_is_not_upcoming(self):
        chosen = next_round.select(
            live_fixtures=[live("Fulham", "Chelsea", 26), live("Arsenal", "Coventry", -40)],
            enrichment=[],
            now=at(0),
        )
        assert [f["home_team_raw"] for f in chosen] == ["Fulham"]

    def test_it_takes_the_next_cluster_not_the_whole_season(self):
        chosen = next_round.select(
            live_fixtures=[
                live("Fulham", "Chelsea", 26),
                live("Palace", "Man City", 30),
                live("Spurs", "Newcastle", 24 * 30),   # a month away
            ],
            enrichment=[],
            now=at(0),
        )
        names = {f["home_team_raw"] for f in chosen}
        assert names == {"Fulham", "Palace"}, "a month away is not this round"

    def test_it_returns_nothing_rather_than_a_played_round(self):
        chosen = next_round.select(
            live_fixtures=[live("Arsenal", "Coventry", -40)], enrichment=[], now=at(0)
        )
        assert chosen == []


class TestEnrichment:
    def test_the_referee_is_joined_on(self):
        chosen = next_round.select(
            live_fixtures=[live("Fulham", "Chelsea", 26)],
            enrichment=[fixture("Fulham", "Chelsea", 26, referee="M Oliver")],
            now=at(0),
        )
        assert chosen[0]["referee_raw"] == "M Oliver"

    def test_a_fixture_with_no_match_still_appears(self):
        """No referee yet is a missing detail, not a reason to drop the game."""
        chosen = next_round.select(
            live_fixtures=[live("Fulham", "Chelsea", 26)], enrichment=[], now=at(0)
        )
        assert len(chosen) == 1
        assert chosen[0]["referee_raw"] is None

    def test_enrichment_never_adds_a_fixture(self):
        """The league's list decides what is played. The other file only decorates."""
        chosen = next_round.select(
            live_fixtures=[live("Fulham", "Chelsea", 26)],
            enrichment=[fixture("Arsenal", "Coventry", 27, referee="X")],
            now=at(0),
        )
        assert len(chosen) == 1
        assert chosen[0]["home_team_raw"] == "Fulham"

    def test_a_kickoff_an_hour_out_still_joins(self):
        """The two sources disagree on exact times more often than on days."""
        chosen = next_round.select(
            live_fixtures=[live("Fulham", "Chelsea", 26)],
            enrichment=[fixture("Fulham", "Chelsea", 26.5, referee="M Oliver")],
            now=at(0),
        )
        assert chosen[0]["referee_raw"] == "M Oliver"


class TestAFixtureWithNoRefereeSurvivesSerialisation:
    """A missing referee becomes NaN once the rows pass through pandas, and NaN
    is not JSON. It reached the site as a literal `NaN` token and broke the
    build. A fixture with no appointment yet is normal, not exceptional.
    """

    def test_missing_values_become_null(self):
        import json

        import numpy as np
        import pandas as pd

        from foulgorithm.publish.player_round import _or_none

        for missing in (None, float("nan"), np.nan, pd.NA, pd.NaT):
            assert _or_none(missing) is None
        assert json.dumps({"referee": _or_none(np.nan)}) == '{"referee": null}'

    def test_a_real_referee_is_untouched(self):
        from foulgorithm.publish.player_round import _or_none

        assert _or_none("M Oliver") == "M Oliver"


class TestSurvivingFootballData:
    def test_a_dead_fixtures_file_does_not_stop_the_round(self, monkeypatch):
        """Between rounds football-data's file is empty and its adapter raises.
        On 25 August 2026 that killed a league publish outright; at T-60 on a
        matchday it would have cost the confirmed elevens. The league's own
        list decides the round; football-data only decorates it."""
        from foulgorithm.sources import football_data, pulselive
        from foulgorithm.sources.base import SourceError

        def dead():
            raise SourceError("no E0 fixtures found. The season may be between rounds.")

        monkeypatch.setattr(football_data, "fetch_fixtures", dead)
        monkeypatch.setattr(
            pulselive,
            "fixtures",
            lambda season_id=None: [
                type("F", (), {"home": "Fulham", "away": "Chelsea", "kickoff_utc": at(2), "complete": False})()
            ],
        )
        chosen = next_round.fetch(now=at(0))
        assert [f["home_team_raw"] for f in chosen] == ["Fulham"]
        assert chosen[0]["referee_raw"] is None
