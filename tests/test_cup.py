"""Cup fixtures are hand-fed and exhibition-only.

The league's feed knows nothing but the Premier League, so a cup tie between
two of our twenty clubs enters through data/cup_fixtures.json by hand. The
engine predicts it exactly as it would a league game, but nothing about it
enters the record: no claims, no slates, no league scoring. A trial is a
trial.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from foulgorithm.publish import cup
from foulgorithm.sources.base import SourceError

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def write(tmp_path: Path, rows) -> Path:
    path = tmp_path / "cup_fixtures.json"
    path.write_text(json.dumps(rows))
    return path


class TestLoadFixtures:
    def test_rows_come_out_shaped_for_the_publisher(self, tmp_path):
        path = write(tmp_path, [{
            "home": "Nott'm Forest", "away": "Leeds",
            "kickoff_utc": "2026-08-25T19:00:00+00:00",
            "competition": "League Cup", "referee": "Andrew Kitchen",
        }])
        rows = cup.load_fixtures(path, now=NOW)
        assert len(rows) == 1
        row = rows[0]
        assert row["home_team_raw"] == "Nott'm Forest"
        assert row["away_team_raw"] == "Leeds"
        assert row["kickoff_utc"] == datetime(2026, 8, 25, 19, 0, tzinfo=timezone.utc)
        assert row["referee_raw"] == "Andrew Kitchen"
        assert row["competition"] == "League Cup"
        assert row["odds_home"] is None

    def test_an_unknown_club_raises_rather_than_guessing(self, tmp_path):
        path = write(tmp_path, [{
            "home": "Nottingham Forest", "away": "Leeds",
            "kickoff_utc": "2026-08-25T19:00:00+00:00",
        }])
        with pytest.raises(SourceError, match="Nottingham Forest"):
            cup.load_fixtures(path, now=NOW)

    def test_a_kickoff_without_a_timezone_raises(self, tmp_path):
        path = write(tmp_path, [{
            "home": "Nott'm Forest", "away": "Leeds",
            "kickoff_utc": "2026-08-25T19:00:00",
        }])
        with pytest.raises(SourceError, match="timezone"):
            cup.load_fixtures(path, now=NOW)

    def test_a_played_fixture_drops_off_the_slate(self, tmp_path):
        path = write(tmp_path, [{
            "home": "Nott'm Forest", "away": "Leeds",
            "kickoff_utc": "2026-08-24T19:00:00+00:00",
        }])
        assert cup.load_fixtures(path, now=NOW) == []

    def test_a_missing_file_is_an_empty_slate(self, tmp_path):
        assert cup.load_fixtures(tmp_path / "absent.json", now=NOW) == []
