"""Pulling the cup rounds, and keeping only the ties we can actually say
something about.

The draw is the draw: an FA Cup third round is 64 clubs and most of them are
outside the two divisions we hold. Those ties are dropped, quietly and without
raising, because a cup round containing Salford is normal rather than broken.

Separation is the other job here. The same two clubs can meet in the league, in
the League Cup and in the FA Cup inside one season, and a two-legged League Cup
semi meets itself. A key built on the club names alone merges all of that, and
the old '-cup' suffix merged the two cups into one page.
"""

from datetime import datetime, timezone

import pytest

from foulgorithm.sources import cup_slate

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def api_row(home, away, kickoff="2026-08-25T19:00:00+00:00", fid=1001, ref="Andrew Kitchen, England", round_="3rd Round"):
    return {
        "fixture": {"id": fid, "date": kickoff, "referee": ref},
        "league": {"round": round_},
        "teams": {"home": {"name": home}, "away": {"name": away}},
    }


class FakeApi:
    CUP_LEAGUES = {45: "FA Cup", 48: "League Cup"}

    def __init__(self, by_league):
        self.by_league = by_league
        self.calls = []

    def _get(self, path, params=None):
        self.calls.append((path, dict(params or {})))
        return {"response": self.by_league.get(params.get("league"), [])}


class TestQualifying:
    def test_a_tie_between_two_premier_league_clubs_is_kept(self):
        api = FakeApi({48: [api_row("Nottingham Forest", "Leeds United")]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert len(out) == 1
        assert out[0]["home_team_raw"] == "Nott'm Forest"

    def test_a_premier_league_v_championship_tie_is_kept(self):
        api = FakeApi({45: [api_row("Arsenal", "Wrexham")]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert len(out) == 1
        assert out[0]["away_team_raw"] == "Wrexham"

    def test_two_championship_clubs_are_kept(self):
        api = FakeApi({45: [api_row("Burnley", "Queens Park Rangers")]})
        assert len(cup_slate.fetch(api=api, now=NOW)) == 1

    def test_a_tie_with_a_league_two_club_is_dropped_silently(self):
        api = FakeApi({45: [api_row("Arsenal", "Salford City")]})
        assert cup_slate.fetch(api=api, now=NOW) == []

    def test_a_tie_between_two_clubs_we_hold_nothing_for_is_dropped(self):
        api = FakeApi({45: [api_row("Salford City", "Barnsley")]})
        assert cup_slate.fetch(api=api, now=NOW) == []

    def test_a_kickoff_already_past_is_dropped(self):
        api = FakeApi({48: [api_row("Arsenal", "Leeds United",
                                    kickoff="2026-08-19T19:00:00+00:00")]})
        assert cup_slate.fetch(api=api, now=NOW) == []


class TestBothCups:
    def test_both_cups_are_asked(self):
        api = FakeApi({})
        cup_slate.fetch(api=api, now=NOW)
        assert sorted(c[1]["league"] for c in api.calls) == [45, 48]

    def test_each_tie_carries_the_cup_it_belongs_to(self):
        api = FakeApi({
            45: [api_row("Arsenal", "Wrexham", fid=1)],
            48: [api_row("Chelsea", "Burnley", fid=2)],
        })
        out = cup_slate.fetch(api=api, now=NOW)
        assert {t["competition"] for t in out} == {"FA Cup", "League Cup"}

    def test_the_round_is_carried_through(self):
        api = FakeApi({45: [api_row("Arsenal", "Wrexham", round_="4th Round")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["round"] == "4th Round"

    def test_the_referee_is_normalised_for_joining_and_kept_for_display(self):
        api = FakeApi({45: [api_row("Arsenal", "Wrexham")]})
        tie = cup_slate.fetch(api=api, now=NOW)[0]
        assert tie["referee_raw"] == "A Kitchen"
        assert tie["referee_display"] == "Andrew Kitchen"

    def test_a_tie_with_no_referee_appointed_yet_is_honest(self):
        api = FakeApi({45: [api_row("Arsenal", "Wrexham", ref=None)]})
        tie = cup_slate.fetch(api=api, now=NOW)[0]
        assert tie["referee_raw"] is None


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
        # A replay, or the second leg of a League Cup semi.
        first = cup_slate.slug("Arsenal", "Chelsea", "League Cup")
        second = cup_slate.slug("Arsenal", "Chelsea", "League Cup", repeat=2)
        assert second == "arsenal-v-chelsea-league-cup-2"
        assert first != second

    def test_repeat_slugs_are_assigned_in_kickoff_order(self):
        api = FakeApi({48: [
            api_row("Arsenal", "Chelsea", kickoff="2027-02-01T20:00:00+00:00", fid=2),
            api_row("Arsenal", "Chelsea", kickoff="2027-01-10T20:00:00+00:00", fid=1),
        ]})
        out = cup_slate.fetch(api=api, now=NOW)
        assert [t["slug"] for t in out] == [
            "arsenal-v-chelsea-league-cup",
            "arsenal-v-chelsea-league-cup-2",
        ]

    def test_the_same_pairing_in_each_cup_does_not_count_as_a_repeat(self):
        api = FakeApi({
            45: [api_row("Arsenal", "Chelsea", fid=1)],
            48: [api_row("Arsenal", "Chelsea", fid=2)],
        })
        slugs = {t["slug"] for t in cup_slate.fetch(api=api, now=NOW)}
        assert slugs == {"arsenal-v-chelsea-fa-cup", "arsenal-v-chelsea-league-cup"}


class TestTieKind:
    def test_two_premier_league_clubs_can_carry_the_full_model(self):
        api = FakeApi({48: [api_row("Nottingham Forest", "Leeds United")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["kind"] == "full"

    def test_any_championship_club_drops_the_tie_to_match_total_only(self):
        # No player data exists for the second tier at any price, so a player
        # pick here would be a positional prior wearing a probability.
        api = FakeApi({45: [api_row("Arsenal", "Wrexham")]})
        assert cup_slate.fetch(api=api, now=NOW)[0]["kind"] == "total"
