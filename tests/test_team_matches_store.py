"""Reading twenty seasons of team match stats into one tidy table.

One row per team per match, every stat a column. Same validation discipline as
the season store: a file whose row count disagrees with its contents is a
truncated write and is rejected here rather than surfacing as a strange number
inside a model.

The join key matters. Every row carries `fixtureId`, `teamId`, and the two club
names, so it can be matched to our own fixtures without guessing.
"""

import json

import pytest

from foulgorithm.store import team_matches as tm


def season_file(tmp_path, label="2024-25", teams=None, **kw):
    payload = {
        "season": label.replace("-", "/"),
        "seasonId": 719,
        "source": "https://example/stats/match/{fixture_id}",
        "fetchedAt": "2026-08-24T00:00:00+00:00",
        "rows": len(teams or []),
        "teams": teams or [],
    }
    payload.update(kw)
    (tmp_path / f"{label}.json").write_text(json.dumps(payload))
    return tmp_path


def team(fixture=1, team_id="1", **kw):
    base = {
        "fixtureId": fixture,
        "teamId": team_id,
        "home": "Arsenal",
        "away": "Coventry",
        "kickoff": "21 August 2026",
        "fk_foul_lost": 12,
        "fk_foul_won": 10,
        "touches": 900,
    }
    base.update(kw)
    return base


class TestLoading:
    def test_it_reads_a_season(self, tmp_path):
        season_file(tmp_path, teams=[team()])
        d = tm.load(tmp_path)
        assert len(d) == 1
        assert d.iloc[0]["fk_foul_lost"] == 12

    def test_seasons_stack(self, tmp_path):
        season_file(tmp_path, "2024-25", [team()])
        season_file(tmp_path, "2023-24", [team(fixture=2)])
        assert len(tm.load(tmp_path)) == 2

    def test_an_empty_directory_is_an_empty_frame(self, tmp_path):
        d = tm.load(tmp_path)
        assert len(d) == 0
        assert "fixtureId" in d.columns

    def test_a_truncated_file_is_rejected(self, tmp_path):
        season_file(tmp_path, teams=[team()], rows=99)
        with pytest.raises(ValueError, match="rows"):
            tm.load(tmp_path)

    def test_provenance_is_required(self, tmp_path):
        season_file(tmp_path, teams=[team()], fetchedAt="")
        with pytest.raises(ValueError, match="fetchedAt"):
            tm.load(tmp_path)


class TestMatchTotals:
    def test_a_match_total_sums_both_teams(self, tmp_path):
        season_file(
            tmp_path,
            teams=[
                team(team_id="1", fk_foul_lost=12),
                team(team_id="5", fk_foul_lost=11),
            ],
        )
        totals = tm.match_totals(tm.load(tmp_path))
        assert len(totals) == 1
        assert totals.iloc[0]["fouls"] == 23

    def test_a_half_recorded_match_is_dropped(self, tmp_path):
        """One team's stats is not a match total, and would read as a quiet game."""
        season_file(tmp_path, teams=[team(team_id="1", fk_foul_lost=12)])
        assert len(tm.match_totals(tm.load(tmp_path))) == 0

    def test_it_keeps_the_clubs_and_kickoff(self, tmp_path):
        season_file(tmp_path, teams=[team(team_id="1"), team(team_id="5")])
        row = tm.match_totals(tm.load(tmp_path)).iloc[0]
        assert row["home"] == "Arsenal" and row["away"] == "Coventry"
