"""Pulling the cup slate, and keeping only the ties we can say something about.

The source is the Premier League's own API, which turns out to carry the FA Cup
(competition 4) and the EFL Cup (competition 5) as well as its own league:
2,730 and 1,676 fixtures respectively, with the referee and the confirmed
elevens attached. It is free, unauthenticated, and already this project's
lineup source, so the cups now run on a source we already depend on rather than
on a second one with its own account to keep alive.

Most of a cup round is dropped, and that is the normal case. An FA Cup third
round is 64 clubs and we hold 44 of the 92 league clubs, so a tie involving
anyone else is skipped without a word.

Separation is the other job here. The same two clubs can meet in the league, in
the League Cup and in the FA Cup inside one season, and a two-legged League Cup
semi meets itself. A key built on the club names alone merges all of that, and
the old '-cup' suffix merged the two cups into one page.
"""

from datetime import datetime, timezone

import pytest

from foulgorithm.sources import cup_slate

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def fixture(home, away, comp="EFL Cup", kickoff_millis=1788289200000, fid=131355,
            referee="Andrew Kitchen", status="U", round_label="Second Round"):
    """One fixture in the shape Pulselive returns."""
    officials = [{"role": "MAIN", "name": {"display": referee}}] if referee else []
    return {
        "id": float(fid),
        "status": status,
        "fixtureType": "CUP",
        "kickoff": {"millis": kickoff_millis, "label": "Tue 1 Sep 2026, 20:00 BST"},
        "teams": [
            {"team": {"id": 1.0, "name": home}},
            {"team": {"id": 2.0, "name": away}},
        ],
        "matchOfficials": officials,
        "gameweek": {"gameweek": 2.0,
                     "competitionPhase": {"label": round_label, "type": "K"},
                     "compSeason": {"label": f"English {comp} Season 2026/2027"}},
    }


class FakeApi:
    """Stands in for sources.pulselive, which reaches the network."""

    CUP_COMPETITIONS = {4: "FA Cup", 5: "League Cup"}

    def __init__(self, by_comp):
        self.by_comp = by_comp
        self.calls = []

    def cup_fixtures(self, comp):
        self.calls.append(comp)
        return list(self.by_comp.get(comp, []))


class TestQualifying:
    def test_a_tie_between_two_premier_league_clubs_is_kept(self):
        api = FakeApi({5: [fixture("Nottingham Forest", "Leeds United")]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert len(out) == 1
        assert out[0]["home_team_raw"] == "Nott'm Forest"
        assert out[0]["away_team_raw"] == "Leeds"

    def test_a_premier_league_v_championship_tie_is_kept(self):
        api = FakeApi({4: [fixture("Arsenal", "Wrexham")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["away_team_raw"] == "Wrexham"

    def test_two_championship_clubs_are_kept(self):
        api = FakeApi({4: [fixture("Burnley", "West Bromwich Albion")]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert out[0]["away_team_raw"] == "West Brom"

    def test_a_tie_with_a_lower_tier_club_is_dropped_silently(self):
        api = FakeApi({5: [fixture("Newcastle United", "Bradford City")]})
        assert cup_slate.fetch(api=api, now=NOW) == []

    def test_a_tie_between_two_clubs_we_hold_nothing_for_is_dropped(self):
        api = FakeApi({4: [fixture("Barnsley", "Crewe Alexandra")]})
        assert cup_slate.fetch(api=api, now=NOW) == []

    def test_a_kickoff_already_past_is_dropped(self):
        past = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
        api = FakeApi({5: [fixture("Arsenal", "Leeds United", kickoff_millis=past)]})
        assert cup_slate.fetch(api=api, now=NOW) == []

    def test_a_completed_tie_is_dropped_even_if_the_clock_says_otherwise(self):
        api = FakeApi({5: [fixture("Arsenal", "Leeds United", status="C")]})
        assert cup_slate.fetch(api=api, now=NOW) == []


class TestBothCups:
    def test_both_cups_are_asked(self):
        api = FakeApi({})
        cup_slate.fetch(api=api, now=NOW)
        assert sorted(api.calls) == [4, 5]

    def test_each_tie_carries_the_cup_it_belongs_to(self):
        api = FakeApi({
            4: [fixture("Arsenal", "Wrexham", comp="FA Cup", fid=1)],
            5: [fixture("Chelsea", "Burnley", comp="EFL Cup", fid=2)],
        })
        out = cup_slate.fetch(api=api, now=NOW)
        assert {t["competition"] for t in out} == {"FA Cup", "League Cup"}

    def test_the_leagues_own_efl_cup_name_becomes_ours(self):
        # Pulselive says "EFL Cup". Every slug, file and page in this project
        # says "League Cup", and one spelling has to win.
        api = FakeApi({5: [fixture("Arsenal", "Leeds United")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["competition"] == "League Cup"

    def test_the_round_is_named_not_numbered(self):
        # The sibling `gameweek` field is a number and renders as "2.0", which
        # is not what any cup round is called.
        api = FakeApi({4: [fixture("Arsenal", "Wrexham", round_label="3rd Round")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["round"] == "3rd Round"

    def test_a_tie_with_no_round_label_is_honest_rather_than_wrong(self):
        f = fixture("Arsenal", "Wrexham")
        f["gameweek"].pop("competitionPhase")
        assert cup_slate.fetch(api=FakeApi({4: [f]}), now=NOW)[0]["round"] is None


class TestReferee:
    def test_the_main_official_is_taken_and_normalised_for_joining(self):
        api = FakeApi({5: [fixture("Arsenal", "Leeds United")]})
        tie = cup_slate.fetch(api=api, now=NOW)[0]
        # football-data writes "A Kitchen"; this is what makes the join land.
        assert tie["referee_raw"] == "A Kitchen"
        assert tie["referee_display"] == "Andrew Kitchen"

    def test_an_assistant_is_never_mistaken_for_the_referee(self):
        f = fixture("Arsenal", "Leeds United", referee=None)
        f["matchOfficials"] = [{"role": "ASSISTANT1", "name": {"display": "Mark Stevens"}}]
        api = FakeApi({5: [f]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["referee_raw"] is None

    def test_a_tie_with_no_official_appointed_yet_is_honest(self):
        api = FakeApi({5: [fixture("Arsenal", "Leeds United", referee=None)]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["referee_raw"] is None


class TestSeparation:
    def test_the_two_cups_get_different_slugs(self):
        fa = cup_slate.slug("Arsenal", "Chelsea", "FA Cup")
        lc = cup_slate.slug("Arsenal", "Chelsea", "League Cup")
        assert fa == "arsenal-v-chelsea-fa-cup"
        assert lc == "arsenal-v-chelsea-league-cup"
        assert fa != lc

    def test_neither_collides_with_the_league_fixture(self):
        from foulgorithm.publish.archive import fixture_slug
        assert cup_slate.slug("Arsenal", "Chelsea", "FA Cup") != fixture_slug("Arsenal v Chelsea")

    def test_a_repeat_tie_in_the_same_cup_gets_its_own_slug(self):
        first = cup_slate.slug("Arsenal", "Chelsea", "League Cup")
        second = cup_slate.slug("Arsenal", "Chelsea", "League Cup", repeat=2)
        assert second == "arsenal-v-chelsea-league-cup-2"
        assert first != second

    def test_repeat_slugs_are_assigned_in_kickoff_order(self):
        later = 1790000000000
        earlier = 1789000000000
        api = FakeApi({5: [
            fixture("Arsenal", "Chelsea", kickoff_millis=later, fid=2),
            fixture("Arsenal", "Chelsea", kickoff_millis=earlier, fid=1),
        ]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert [t["slug"] for t in out] == [
            "arsenal-v-chelsea-league-cup",
            "arsenal-v-chelsea-league-cup-2",
        ]

    def test_the_same_pairing_in_each_cup_does_not_count_as_a_repeat(self):
        api = FakeApi({
            4: [fixture("Arsenal", "Chelsea", comp="FA Cup", fid=1)],
            5: [fixture("Arsenal", "Chelsea", comp="EFL Cup", fid=2)],
        })
        slugs = {t["slug"] for t in cup_slate.fetch(api=api, now=NOW)}
        assert slugs == {"arsenal-v-chelsea-fa-cup", "arsenal-v-chelsea-league-cup"}


class TestTieKind:
    def test_two_premier_league_clubs_can_carry_the_full_model(self):
        api = FakeApi({5: [fixture("Nottingham Forest", "Leeds United")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["kind"] == "full"

    def test_any_championship_club_drops_the_tie_to_match_total_only(self):
        api = FakeApi({4: [fixture("Arsenal", "Wrexham")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["kind"] == "total"


class TestFixtureId:
    def test_the_id_is_an_int_not_the_float_json_gave_us(self):
        # Pulselive rejects "131355.0" with a 400 that reads like a missing
        # fixture rather than a formatting error. See sources/pulselive.
        api = FakeApi({5: [fixture("Arsenal", "Leeds United", fid=131355)]})
        fid = cup_slate.fetch(api=api, now=NOW)[0]["fixture_id"]
        assert fid == 131355 and isinstance(fid, int)
