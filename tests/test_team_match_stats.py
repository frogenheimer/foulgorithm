"""Around 180 team stats per match, twenty seasons, from the league's own API.

We hold about six team stats a match from football-data.co.uk. This is roughly
thirty times richer and covers the same 2006/07 boundary as everything else the
league publishes.

Nothing here touches the network. What matters is the shape: a fixture that
returns nothing must not be written as though it were played, both teams have to
survive, and every file has to say when it was fetched.
"""

import json

import pytest

from foulgorithm.sources import team_match_stats as tms


def payload(home_id="1", away_id="5", stats=(("fk_foul_lost", 12), ("touches", 900))):
    return {
        "data": {
            home_id: {"M": [{"name": n, "value": v} for n, v in stats]},
            away_id: {"M": [{"name": n, "value": v + 1} for n, v in stats]},
        }
    }


class TestShapingOneMatch:
    def test_both_teams_come_back(self):
        rows = tms.shape(101, payload())
        assert len(rows) == 2

    def test_stats_land_as_columns(self):
        rows = tms.shape(101, payload())
        assert rows[0]["fk_foul_lost"] == 12
        assert rows[0]["touches"] == 900

    def test_every_row_carries_the_fixture_and_team(self):
        rows = tms.shape(101, payload())
        assert all(r["fixtureId"] == 101 for r in rows)
        assert {r["teamId"] for r in rows} == {"1", "5"}

    def test_a_match_with_no_data_returns_nothing(self):
        assert tms.shape(101, {"data": {}}) == []
        assert tms.shape(101, {}) == []

    def test_a_team_with_no_stats_is_dropped_not_blanked(self):
        """An empty stat block means not recorded, not a goalless defensive display."""
        raw = payload()
        raw["data"]["5"] = {"M": []}
        rows = tms.shape(101, raw)
        assert len(rows) == 1
        assert rows[0]["teamId"] == "1"


class TestWriting:
    def test_a_season_records_when_it_was_fetched(self, tmp_path):
        path = tms.write_season(tmp_path, "2024/25", 719, [{"fixtureId": 1, "teamId": "1"}])
        held = json.loads(path.read_text())
        assert held["season"] == "2024/25"
        assert held["fetchedAt"]
        assert held["rows"] == 1
        assert held["source"].startswith("http")

    def test_an_empty_season_is_not_written(self, tmp_path):
        assert tms.write_season(tmp_path, "2024/25", 719, []) is None
        assert list(tmp_path.glob("*.json")) == []

    def test_the_row_count_matches(self, tmp_path):
        rows = [{"fixtureId": i, "teamId": "1"} for i in range(19)]
        path = tms.write_season(tmp_path, "2024/25", 719, rows)
        assert json.loads(path.read_text())["rows"] == 19
