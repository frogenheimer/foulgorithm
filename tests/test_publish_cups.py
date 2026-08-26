"""The cup payload's contract, which is mostly about what is NOT in it.

Three rules, and the first is the one worth breaking the build over.

**No player-level number may appear for a tie involving a Championship club.**
No player foul data exists for the second tier at any price, so anything
player-shaped there would be a positional prior wearing a probability. The
publisher must not be able to emit one even by accident.

**Nothing is recorded.** Cups are exhibition. No claim, no slate, no league
scoring, no track-record noise from games our results source will never grade.

**The two cups never share a page.** Separate files, separate slugs, and no
cup slug ever equal to a league fixture's.
"""

from datetime import datetime, timezone

import pytest

from foulgorithm.publish import cups

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def tie(home, away, competition="FA Cup", kind="total", slug=None, kickoff="2026-09-01T19:00:00+00:00"):
    from foulgorithm.sources import cup_slate
    return {
        "home_team_raw": home, "away_team_raw": away,
        "kickoff_utc": datetime.fromisoformat(kickoff),
        "known_at": NOW,
        "referee_raw": "A Kitchen", "referee_display": "Andrew Kitchen",
        "competition": competition, "round": "3rd Round",
        "fixture_id": 1, "kind": kind, "source": "api-football",
        "slug": slug or cup_slate.slug(home, away, competition),
        "odds_home": None, "odds_draw": None, "odds_away": None,
    }


def history():
    from tests.test_team_record import match
    rows = []
    for i in range(30):
        rows.append({**match("Arsenal", "Chelsea", hf=10, af=12, hy=2, ay=1),
                     "kickoff_utc": f"2026-0{i % 8 + 1}-01"})
        rows.append({**match("Wrexham", "Burnley", hf=14, af=9, hy=3, ay=2,
                             season="2026-27", division="E1"),
                     "kickoff_utc": f"2026-0{i % 8 + 1}-02"})
    return rows


class TestNoPlayerNumbers:
    """The rule that must not be breakable."""

    # "board" is on the list on purpose: everywhere else in this codebase it
    # means the PLAYER board, and a cup payload must never grow one. The
    # fixture list here is called "ties" so the check can stay this strict.
    FORBIDDEN = ("houseSheet", "picks", "players", "board", "slips",
                 "outOf100", "fairOdds", "expectedMinutes", "ratePer90")

    @staticmethod
    def carrying(node, keys, path="payload"):
        """Every forbidden key holding an actual VALUE, with where it was.

        A key present and explicitly null is fine and is more honest to a
        reader of the JSON than a missing one. A key with something in it is
        the failure.
        """
        found = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k in keys and v not in (None, [], {}):
                    found.append(f"{path}.{k}")
                found += TestNoPlayerNumbers.carrying(v, keys, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                found += TestNoPlayerNumbers.carrying(v, keys, f"{path}[{i}]")
        return found

    def test_a_cross_division_tie_carries_nothing_player_shaped(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert self.carrying(payload, self.FORBIDDEN) == []

    def test_the_check_would_actually_catch_one(self):
        # A guard on the guard. A test that cannot fail is not a test.
        leaky = {"ties": [{"houseSheet": {"groups": [1]}}]}
        assert self.carrying(leaky, self.FORBIDDEN) == ["payload.ties[0].houseSheet"]

    def test_a_cross_division_tie_is_marked_as_stats_and_total_only(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["kind"] == "total"

    def test_a_championship_only_tie_is_the_same(self):
        payload = cups.build([tie("Wrexham", "Burnley")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["kind"] == "total"
        assert self.carrying(payload, self.FORBIDDEN) == []


class TestExhibition:
    def test_the_payload_says_nothing_here_is_recorded(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["recorded"] is False

    def test_no_slate_or_claim_structure_is_written(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert "slates" not in payload
        assert "standings" not in payload


class TestSeparation:
    def test_one_payload_holds_one_cup_only(self):
        payload = cups.build(
            [tie("Arsenal", "Wrexham", "FA Cup"), tie("Chelsea", "Burnley", "League Cup")],
            history(), {}, {}, competition="FA Cup", now=NOW,
        )
        assert {t["competition"] for t in payload["ties"]} == {"FA Cup"}

    def test_every_slug_in_a_payload_is_unique(self):
        payload = cups.build(
            [tie("Arsenal", "Wrexham"), tie("Chelsea", "Burnley")],
            history(), {}, {}, now=NOW,
        )
        slugs = [t["slug"] for t in payload["ties"]]
        assert len(slugs) == len(set(slugs))

    def test_no_cup_slug_equals_its_league_fixtures_slug(self):
        from foulgorithm.publish.archive import fixture_slug
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["slug"] != fixture_slug("Arsenal v Wrexham")


class TestContent:
    def test_each_tie_carries_the_comparison_blocks(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert [b["title"] for b in payload["ties"][0]["compare"]][0] == "Fouls"

    def test_each_tie_carries_the_referee_record(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["referee"]["referee"] == "Andrew Kitchen"

    def test_a_cross_division_tie_carries_its_scale_warning(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["crossDivision"] is not None

    def test_a_same_division_tie_does_not(self):
        payload = cups.build([tie("Wrexham", "Burnley")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["crossDivision"] is None

    def test_each_side_carries_its_spell_label(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert "Premier League" in payload["ties"][0]["record"]["home"]["spell"]


class TestEmptySlate:
    def test_no_ties_still_writes_an_honest_payload(self):
        payload = cups.build([], history(), {}, {}, competition="FA Cup", now=NOW)
        assert payload["ties"] == []
        assert payload["competition"] == "FA Cup"


class TestHouseSheetGating:
    """Picks reach a Premier League tie and nothing else.

    This is the same rule as TestNoPlayerNumbers seen from the other side: it
    is not enough that a Championship tie has no house sheet by accident of the
    model failing. The publisher must refuse to build one.
    """

    SHEET = {"groups": [{"market": "committed", "line": 1,
                         "picks": [{"player": "Bukayo Saka", "outOf100": 62, "star": True}]}]}

    def test_a_premier_league_tie_takes_the_house_sheet(self):
        payload = cups.build(
            [tie("Arsenal", "Chelsea", kind="full")], history(), {}, {},
            sheets={"arsenal-v-chelsea-fa-cup": self.SHEET}, now=NOW,
        )
        assert payload["ties"][0]["houseSheet"] == self.SHEET

    def test_a_championship_tie_refuses_one_even_when_handed_it(self):
        # Handed a sheet on purpose. It must not land.
        payload = cups.build(
            [tie("Arsenal", "Wrexham", kind="total")], history(), {}, {},
            sheets={"arsenal-v-wrexham-fa-cup": self.SHEET}, now=NOW,
        )
        assert payload["ties"][0]["houseSheet"] is None
        assert "Bukayo Saka" not in str(payload)

    def test_a_tie_marked_full_but_holding_a_championship_club_is_downgraded(self):
        # Belt and braces: if the slate ever mislabels a tie, the publisher
        # still refuses. The club list is the authority, not the label.
        payload = cups.build(
            [tie("Arsenal", "Wrexham", kind="full")], history(), {}, {},
            sheets={"arsenal-v-wrexham-fa-cup": self.SHEET}, now=NOW,
        )
        assert payload["ties"][0]["kind"] == "total"
        assert payload["ties"][0]["houseSheet"] is None


class TestLineups:
    """Confirmed elevens, shown as names and nothing else.

    A Premier League XI could carry each player's foul rate and a Championship
    one could not, so showing rates would make the two sides of a cross-division
    tie asymmetric in exactly the way the rest of the page refuses to be. Names
    on both sides, and the picks live in the house sheet where they belong.
    """

    def test_a_confirmed_eleven_reaches_its_tie(self):
        sheets = {"Arsenal|Arsenal v Wrexham": _lineup("4-3-3", ["Raya", "Saliba"]),
                  "Wrexham|Arsenal v Wrexham": _lineup("4-4-2", ["Okonkwo", "O'Connor"])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             lineups=sheets, now=NOW)
        lu = payload["ties"][0]["lineups"]
        assert lu["home"]["formation"] == "4-3-3"
        assert lu["away"]["starters"] == ["Okonkwo", "O'Connor"]

    def test_a_tie_with_no_eleven_yet_says_so(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["lineups"] is None

    def test_one_side_confirmed_is_not_pretended_to_be_both(self):
        sheets = {"Arsenal|Arsenal v Wrexham": _lineup("4-3-3", ["Raya"])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             lineups=sheets, now=NOW)
        lu = payload["ties"][0]["lineups"]
        assert lu["home"] is not None
        assert lu["away"] is None

    def test_another_ties_eleven_does_not_leak_in(self):
        sheets = {"Chelsea|Chelsea v Burnley": _lineup("4-3-3", ["Sanchez"])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             lineups=sheets, now=NOW)
        assert payload["ties"][0]["lineups"] is None

    def test_no_player_rate_travels_with_an_eleven(self):
        sheets = {"Arsenal|Arsenal v Wrexham": _lineup("4-3-3", ["Raya"])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             lineups=sheets, now=NOW)
        assert TestNoPlayerNumbers.carrying(payload, TestNoPlayerNumbers.FORBIDDEN) == []


def _lineup(formation, starters):
    from types import SimpleNamespace
    return SimpleNamespace(formation=formation, starters=starters,
                           lines=[], bench=[])


class TestRefereePending:
    """The official is not named until kickoff, and the page must say so.

    Pulselive carries `matchOfficials` on a played fixture and an empty list on
    an upcoming one, so a cup page built before kickoff has no referee. Letting
    the block vanish reads as "we have nothing on this official", which is a
    different and wrong claim: we have plenty, we just do not know which one it
    is yet.
    """

    def test_an_unnamed_official_is_reported_as_pending(self):
        t = tie("Arsenal", "Wrexham")
        t["referee_raw"] = None
        t["referee_display"] = None
        payload = cups.build([t], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["referee"] is None
        assert payload["ties"][0]["refereePending"] is True

    def test_a_named_official_is_not_pending(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["referee"] is not None
        assert payload["ties"][0]["refereePending"] is False
