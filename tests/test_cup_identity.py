"""A cup tie must never be mistaken for the league game between the same clubs.

On 25 August 2026 the League Cup's Nott'm Forest v Leeds silently took over the
league fixture's page and filed its expected-fouls claim against the league
match that had already been played. The fix was a '-cup' suffix.

That suffix is no longer enough. Two domestic cups means Arsenal v Chelsea can
happen in both, and a replay or a two-legged semi means it can happen twice in
one of them. All of those were one URL. Cup identity is now qualified by the
competition and, where needed, by which meeting it is.

Also holds the lineup and wake tests that lived in tests/test_cup.py before the
hand-fed slate was retired.
"""

from datetime import datetime, timedelta, timezone

import pytest


class TestArchiveSlug:
    def test_a_league_slice_keeps_the_plain_slug(self):
        from foulgorithm.publish import archive
        assert archive.slice_payload(_payload(None), "A v B")["slug"] == "a-v-b"

    def test_a_league_cup_slice_names_its_cup(self):
        from foulgorithm.publish import archive
        held = archive.slice_payload(_payload("League Cup"), "A v B")
        assert held["slug"] == "a-v-b-league-cup"

    def test_an_fa_cup_slice_names_its_cup(self):
        from foulgorithm.publish import archive
        held = archive.slice_payload(_payload("FA Cup"), "A v B")
        assert held["slug"] == "a-v-b-fa-cup"

    def test_the_two_cups_never_share_a_page(self):
        from foulgorithm.publish import archive
        fa = archive.slice_payload(_payload("FA Cup"), "A v B")["slug"]
        lc = archive.slice_payload(_payload("League Cup"), "A v B")["slug"]
        assert fa != lc

    def test_no_cup_slug_equals_the_league_fixtures(self):
        from foulgorithm.publish import archive
        league = archive.slice_payload(_payload(None), "A v B")["slug"]
        for cup in ("FA Cup", "League Cup"):
            assert archive.slice_payload(_payload(cup), "A v B")["slug"] != league

    def test_an_unrecognised_competition_still_separates_from_the_league(self):
        # A cup we have not modelled must not silently land on the league page.
        from foulgorithm.publish import archive
        held = archive.slice_payload(_payload("Community Shield"), "A v B")
        assert held["slug"] != "a-v-b"


class TestShapeLineups:
    """API-Football's lineup payload becomes the same ConfirmedLineup shape
    the league feed produces, so the publisher cannot tell the sources apart."""

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
            "startXI": [{"player": {"name": "L.Perri", "number": 1, "pos": "G", "grid": "1:1"}}],
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
        assert [s.name for s in forest.lines[1]] == ["O.Aina", "Murillo"]
        assert forest.bench[0].name == "C.Hutchinson"

    def test_a_championship_club_now_shapes_rather_than_raising(self):
        # Wrexham used to raise here. They are in the Championship now and a
        # cup tie of theirs is one we publish, so their eleven must shape.
        from foulgorithm.sources import api_football
        rows = [{"team": {"name": "Wrexham"}, "formation": "4-4-2",
                 "startXI": [{"player": {"name": "A.Okonkwo", "number": 1, "pos": "G", "grid": "1:1"}}],
                 "substitutes": []}]
        out = api_football.shape_lineups(rows, "Arsenal v Wrexham")
        assert out["Wrexham|Arsenal v Wrexham"].formation == "4-4-2"

    def test_a_team_we_cannot_name_raises(self):
        from foulgorithm.sources import api_football
        from foulgorithm.sources.base import SourceError
        broken = [{"team": {"name": "Salford City"}, "formation": None,
                   "startXI": [], "substitutes": []}]
        with pytest.raises(SourceError, match="Salford City"):
            api_football.shape_lineups(broken, "Nott'm Forest v Leeds")


class TestCupWakes:
    """The lineup wakes cover cup kickoffs too; the settle wakes never do,
    because an exhibition has nothing to settle."""

    def test_cup_kickoffs_join_the_lineup_windows(self):
        from types import SimpleNamespace
        from foulgorithm.jobs import schedule

        now = datetime.now(timezone.utc)
        league = [SimpleNamespace(kickoff_utc=now + timedelta(days=4))]
        cup = [SimpleNamespace(kickoff_utc=now + timedelta(days=1))]
        assert len(schedule.windows(league + cup)) == 2


def _payload(competition):
    return {
        "generatedAt": "2026-08-25T17:00:00+00:00",
        "fixtureSlips": {"A v B": {"alan": [{"legs": []}]}},
        "board": [{"home": "A", "away": "B", "kickoff": "k", "competition": competition}],
        "picks": [],
    }
