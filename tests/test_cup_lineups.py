"""Confirmed cup elevens, from the source that already supplies the league's.

The old watcher polled API-Football per fixture, which cost about 47 requests
for one tie against a free cap of 100 a day. Ten qualifying ties would have
been 470 and the watch would have died mid-round. That whole problem is gone
rather than solved: the league's own API needs no key, meters no daily quota,
and carries `teamLists` on a cup fixture in exactly the shape it carries them
on a league one, so the existing lineup machinery reads both.

What survives from the old design is the caution. Polling stays gentle because
the source is free and run by somebody else, and the watch still gives up at
kickoff rather than grinding on.
"""

import pytest

from foulgorithm.jobs import cup_watch


def team_list(team_id, formation, names):
    return {
        "teamId": float(team_id),
        "formation": {"label": formation},
        "lineup": [
            {"name": {"display": n}, "matchPosition": "M", "matchShirtNumber": i + 1,
             "info": {"position": "M"}}
            for i, n in enumerate(names)
        ],
        "substitutes": [],
    }


def detail(home="Nottingham Forest", away="Leeds United", lists=True):
    d = {
        "id": 131355.0,
        "teams": [{"team": {"id": 15.0, "name": home}}, {"team": {"id": 9.0, "name": away}}],
        "matchOfficials": [{"role": "MAIN", "name": {"display": "Andrew Kitchen"}}],
        "teamLists": [],
    }
    if lists:
        d["teamLists"] = [
            team_list(15, "3-4-3", ["M.Sels", "Murillo", "O.Aina"]),
            team_list(9, "4-1-4-1", ["L.Perri", "J.Bogle"]),
        ]
    return d


class FakeApi:
    STATUS_COMPLETE = "C"

    def __init__(self, details):
        self.details = details
        self.calls = []

    def fixture_detail(self, fixture_id):
        self.calls.append(fixture_id)
        return self.details.get(fixture_id, {})


class TestShaping:
    def test_elevens_come_back_keyed_like_the_league_feed(self):
        api = FakeApi({131355: detail()})
        out = cup_watch.lineups_for(131355, "Nott'm Forest v Leeds", api=api)
        assert set(out) == {
            "Nott'm Forest|Nott'm Forest v Leeds",
            "Leeds|Nott'm Forest v Leeds",
        }

    def test_the_formation_and_starters_survive(self):
        api = FakeApi({131355: detail()})
        out = cup_watch.lineups_for(131355, "Nott'm Forest v Leeds", api=api)
        forest = out["Nott'm Forest|Nott'm Forest v Leeds"]
        assert forest.formation == "3-4-3"
        assert forest.starters[0] == "M.Sels"

    def test_a_fixture_with_no_team_lists_yet_returns_nothing(self):
        # Normal until roughly an hour before kickoff. Not an error.
        api = FakeApi({131355: detail(lists=False)})
        assert cup_watch.lineups_for(131355, "Nott'm Forest v Leeds", api=api) == {}

    def test_one_request_per_fixture_and_no_more(self):
        api = FakeApi({131355: detail()})
        cup_watch.lineups_for(131355, "Nott'm Forest v Leeds", api=api)
        assert api.calls == [131355]

    def test_a_championship_club_shapes_rather_than_raising(self):
        api = FakeApi({99: detail(home="Arsenal", away="Wrexham")})
        api.details[99]["teams"] = [
            {"team": {"id": 15.0, "name": "Arsenal"}},
            {"team": {"id": 9.0, "name": "Wrexham"}},
        ]
        out = cup_watch.lineups_for(99, "Arsenal v Wrexham", api=api)
        assert "Wrexham|Arsenal v Wrexham" in out

    def test_a_club_outside_our_two_divisions_is_skipped_not_fatal(self):
        api = FakeApi({99: detail(home="Arsenal", away="Bradford City")})
        api.details[99]["teams"] = [
            {"team": {"id": 15.0, "name": "Arsenal"}},
            {"team": {"id": 9.0, "name": "Bradford City"}},
        ]
        out = cup_watch.lineups_for(99, "Arsenal v Bradford City", api=api)
        assert set(out) == {"Arsenal|Arsenal v Bradford City"}


class TestCadence:
    def test_the_window_opens_well_before_kickoff(self):
        # The league posts at about T-60. Cup elevens are no more punctual, so
        # the watch opens earlier and that must not regress.
        assert cup_watch.LOOK_FROM.total_seconds() >= 70 * 60

    def test_polling_stays_gentle(self):
        # No quota forces this any more. It stays because the source is free
        # and somebody else pays to run it.
        assert cup_watch.POLL_SECONDS >= 120

    def test_the_watch_gives_up_rather_than_grinding(self):
        assert cup_watch.MAX_RUNTIME.total_seconds() <= 4 * 3600


class TestBeforeKickoff:
    """What the source actually returns before the sheets are in.

    Not an empty list. Pulselive returns `teamLists: [null, null]`, two null
    placeholders where the elevens will go, and calling .get() on those is an
    AttributeError rather than a graceful empty. It would have taken down the
    LEAGUE watcher too, since both read the same shaper.
    """

    def test_null_placeholders_are_skipped_not_crashed_on(self):
        api = FakeApi({131352: {
            "id": 131352.0,
            "teams": [{"team": {"id": 15.0, "name": "Fulham"}},
                      {"team": {"id": 9.0, "name": "Leeds United"}}],
            "teamLists": [None, None],
        }})
        assert cup_watch.lineups_for(131352, "Fulham v Leeds", api=api) == {}

    def test_one_side_named_and_one_still_null(self):
        api = FakeApi({131352: {
            "id": 131352.0,
            "teams": [{"team": {"id": 15.0, "name": "Nottingham Forest"}},
                      {"team": {"id": 9.0, "name": "Leeds United"}}],
            "teamLists": [team_list(15, "3-4-3", ["M.Sels"]), None],
        }})
        out = cup_watch.lineups_for(131352, "Nott'm Forest v Leeds", api=api)
        assert set(out) == {"Nott'm Forest|Nott'm Forest v Leeds"}
