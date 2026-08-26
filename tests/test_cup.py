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


class TestToFixtureName:
    """API-Football spells clubs a fourth way, so every spelling any source
    uses must resolve to the fixture-source name or to None, never to a
    guess."""

    def test_full_names_resolve(self):
        from foulgorithm.identity.teams import to_fixture_name
        assert to_fixture_name("Nottingham Forest") == "Nott'm Forest"
        assert to_fixture_name("Manchester United") == "Man United"
        assert to_fixture_name("Leeds United") == "Leeds"

    def test_fixture_and_fpl_spellings_resolve_too(self):
        from foulgorithm.identity.teams import to_fixture_name
        assert to_fixture_name("Leeds") == "Leeds"
        assert to_fixture_name("Nott'm Forest") == "Nott'm Forest"
        assert to_fixture_name("Man Utd") == "Man United"
        assert to_fixture_name("Spurs") == "Tottenham"

    def test_an_unknown_club_is_none_not_a_guess(self):
        from foulgorithm.identity.teams import to_fixture_name
        # Salford are League Two. Wrexham used to be the example here and can
        # no longer be: they are in the Championship, which we now hold.
        assert to_fixture_name("Salford City") is None


class TestShapeLineups:
    """API-Football's lineup payload becomes the same ConfirmedLineup shape
    the league feed produces, so publish() cannot tell the sources apart."""

    RESPONSE = [
        {
            "team": {"name": "Nottingham Forest"},
            "formation": "4-2-3-1",
            "startXI": [
                {"player": {"name": "M.Turner", "number": 1, "pos": "G", "grid": "1:1"}},
                {"player": {"name": "O.Aina", "number": 43, "pos": "D", "grid": "2:1"}},
                {"player": {"name": "Murillo", "number": 40, "pos": "D", "grid": "2:2"}},
                {"player": {"name": "I.Sangare", "number": 6, "pos": "M", "grid": "3:1"}},
                {"player": {"name": "C.Wood", "number": 11, "pos": "F", "grid": "4:1"}},
            ],
            "substitutes": [
                {"player": {"name": "C.Hutchinson", "number": 30, "pos": "F", "grid": None}}
            ],
        },
        {
            "team": {"name": "Leeds"},
            "formation": "4-1-4-1",
            "startXI": [
                {"player": {"name": "L.Perri", "number": 1, "pos": "G", "grid": "1:1"}}
            ],
            "substitutes": [],
        },
    ]

    def test_keyed_and_shaped_like_the_league_feed(self):
        from foulgorithm.sources import api_football
        label = "Nott'm Forest v Leeds"
        out = api_football.shape_lineups(self.RESPONSE, label)
        assert set(out) == {f"Nott'm Forest|{label}", f"Leeds|{label}"}
        forest = out[f"Nott'm Forest|{label}"]
        assert forest.formation == "4-2-3-1"
        assert forest.starters[0] == "M.Turner"
        assert len(forest.lines) == 4
        assert [s.name for s in forest.lines[0]] == ["M.Turner"]
        assert [s.name for s in forest.lines[1]] == ["O.Aina", "Murillo"]
        assert forest.bench[0].name == "C.Hutchinson"

    def test_a_team_we_cannot_name_raises(self):
        from foulgorithm.sources import api_football
        from foulgorithm.sources.base import SourceError
        broken = [{"team": {"name": "Salford City"}, "formation": None, "startXI": [], "substitutes": []}]
        with pytest.raises(SourceError, match="Salford City"):
            api_football.shape_lineups(broken, "Nott'm Forest v Leeds")


class TestCupWakes:
    """The lineup wakes cover cup kickoffs too; the settle wakes never do,
    because an exhibition has nothing to settle."""

    def test_cup_kickoffs_join_the_lineup_windows(self):
        from types import SimpleNamespace
        from datetime import timedelta
        from foulgorithm.jobs import schedule

        # windows() reads the real clock, so the kickoffs are placed relative
        # to it: one league game in four days, one cup tie tomorrow night.
        now = datetime.now(timezone.utc)
        league = [SimpleNamespace(kickoff_utc=now + timedelta(days=4))]
        cup = [SimpleNamespace(kickoff_utc=now + timedelta(days=1))]
        times = schedule.windows(league + cup)
        assert len(times) == 2


class TestCupIdentity:
    """A cup tie between the same two clubs shares the league fixture's
    label. On 25 Aug 2026 the League Cup's Nott'm Forest v Leeds silently
    took over the league game's page and filed its expected-fouls claim
    under the played league match. Cup identity is qualified everywhere."""

    def test_a_cup_slice_gets_its_own_slug(self):
        from foulgorithm.publish import archive
        payload = {
            "generatedAt": "2026-08-25T17:00:00+00:00",
            "fixtureSlips": {"A v B": {"alan": [{"legs": []}]}},
            "board": [{"home": "A", "away": "B", "kickoff": "k", "competition": "League Cup"}],
            "picks": [],
        }
        held = archive.slice_payload(payload, "A v B")
        assert held["slug"] == "a-v-b-cup"

    def test_a_league_slice_keeps_the_plain_slug(self):
        from foulgorithm.publish import archive
        payload = {
            "generatedAt": "2026-08-25T17:00:00+00:00",
            "fixtureSlips": {"A v B": {"alan": [{"legs": []}]}},
            "board": [{"home": "A", "away": "B", "kickoff": "k", "competition": None}],
            "picks": [],
        }
        assert archive.slice_payload(payload, "A v B")["slug"] == "a-v-b"
