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


class TestPlayers:
    """The players block, which is the half of these pages that was missing.

    Both sides carry it now. The claim that Championship player data does not
    exist was wrong: the league's own API ranks competition 12 as well as
    competition 1, so an XI on either side of a cross-division tie shows the
    same columns rather than one side showing names and the other rates.
    """

    SQUADS = None

    @staticmethod
    def squads():
        from foulgorithm.sources.player_stats import PlayerStats

        def p(name, club, pos="M", mins=900, fouls=10):
            return PlayerStats(
                player=name, player_id=abs(hash(name)) % 9999, club=club,
                position=pos, shirt=None, appearances=10, minutes=mins,
                fouls=fouls, fouls_won=5, tackles=7, yellows=1, reds=0,
                fouls_per_90=round(fouls / (mins / 90), 2), fouls_won_per_90=0.5,
                tackles_per_90=0.7, minutes_by_division={"E0": mins},
            )

        return {
            "Arsenal": [p("Keep Arsenal", "Arsenal", "G", 2000)]
                       + [p(f"Gunner {i}", "Arsenal", mins=1900 - i * 10) for i in range(12)],
            "Wrexham": [p("Keep Wrexham", "Wrexham", "G", 1800)]
                       + [p(f"Red {i}", "Wrexham", mins=1700 - i * 10) for i in range(12)],
        }

    def test_both_sides_get_an_eleven(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), now=NOW)
        players = payload["ties"][0]["players"]
        assert len(players["home"]["players"]) == 11
        assert len(players["away"]["players"]) == 11

    def test_a_championship_side_carries_the_same_columns_as_a_league_one(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), now=NOW)
        home = payload["ties"][0]["players"]["home"]["players"][0]
        away = payload["ties"][0]["players"]["away"]["players"][0]
        assert set(home) == set(away)
        assert away["foulsPer90"] is not None

    def test_an_unconfirmed_eleven_carries_the_rotation_warning(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert block["confirmed"] is False
        assert "rotate" in block["note"].lower()

    def test_a_confirmed_sheet_replaces_the_prediction_and_drops_the_warning(self):
        from types import SimpleNamespace
        sheets = {
            "Arsenal|Arsenal v Wrexham": SimpleNamespace(
                formation="4-3-3", starters=["Gunner 3", "Gunner 4"], lines=[], bench=[]),
        }
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), lineups=sheets, now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert block["confirmed"] is True
        assert block["note"] is None
        assert [p["player"] for p in block["players"]] == ["Gunner 3", "Gunner 4"]

    def test_one_side_confirmed_leaves_the_other_predicted(self):
        from types import SimpleNamespace
        sheets = {"Arsenal|Arsenal v Wrexham": SimpleNamespace(
            formation="4-3-3", starters=["Gunner 3"], lines=[], bench=[])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), lineups=sheets, now=NOW)
        players = payload["ties"][0]["players"]
        assert players["home"]["confirmed"] is True
        assert players["away"]["confirmed"] is False

    def test_a_club_we_have_no_squad_for_is_honest_rather_than_empty(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads={"Arsenal": self.squads()["Arsenal"]}, now=NOW)
        assert payload["ties"][0]["players"]["away"]["players"] == []

    def test_no_squads_at_all_leaves_the_block_absent_not_broken(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {}, now=NOW)
        assert payload["ties"][0]["players"] is None

    #: The structural keys here are legitimate, so this checks the thing the
    #: rule is actually about: a player row must carry facts, never a price or
    #: a probability. Picks live in the house sheet and only a Premier League
    #: tie has one.
    NO_PRICES = ("outOf100", "fairOdds", "fair1", "probOver", "band",
                 "expectedMinutes", "ratePer90", "star", "pick")

    def test_a_player_row_carries_no_probability(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=self.squads(), now=NOW)
        assert TestNoPlayerNumbers.carrying(
            payload["ties"][0]["players"], self.NO_PRICES) == []

    def test_that_check_would_catch_a_price(self):
        leaky = {"players": [{"player": "X", "outOf100": 62}]}
        assert TestNoPlayerNumbers.carrying(leaky, self.NO_PRICES) == [
            "payload.players[0].outOf100"
        ]


class TestPitchShape:
    """Each eleven arrives as lines, so the page can draw a pitch."""

    def test_both_sides_carry_lines(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), now=NOW)
        for side in ("home", "away"):
            lines = payload["ties"][0]["players"][side]["lines"]
            assert sum(len(l) for l in lines) == 11
            assert len(lines[0]) == 1          # the keeper, alone

    def test_a_predicted_shape_is_a_grouping_and_says_so(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert block["formation"] is None
        assert block["grouping"] is not None

    def test_a_confirmed_sheet_carries_the_clubs_real_formation(self):
        from types import SimpleNamespace
        spot = lambda n: SimpleNamespace(name=n)
        sheets = {"Arsenal|Arsenal v Wrexham": SimpleNamespace(
            formation="4-3-3",
            starters=["Keep Arsenal"] + [f"Gunner {i}" for i in range(10)],
            lines=[[spot("Keep Arsenal")], [spot(f"Gunner {i}") for i in range(4)]],
            bench=[])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), lineups=sheets, now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert block["formation"] == "4-3-3"
        assert block["grouping"] is None
        assert [len(l) for l in block["lines"]][:2] == [1, 4]

    def test_the_squad_is_a_superset_of_the_pitch(self):
        # There is no separate bench list any more: the pitch works its own
        # bench out from the squad, which is what the league's pitch does.
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), now=NOW)
        block = payload["ties"][0]["players"]["home"]
        on = {p["player"] for line in block["lines"] for p in line}
        squad = {p["player"] for p in block["squad"]}
        assert on <= squad and len(squad) > len(on)


class TestFullSquad:
    """The whole squad, not just the eleven.

    The eleven answers "who is playing"; the squad answers "who could come on,
    and what happens to the game if he does". A bench that only exists as nine
    names cannot be sorted, compared or read, and the pitch needs the full list
    anyway to work out who is not on it.
    """

    def test_the_full_squad_is_published(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert len(block["squad"]) == len(TestPlayers.squads()["Arsenal"])
        assert len(block["squad"]) > len(block["lines"][0])

    def test_everyone_on_the_pitch_is_in_the_squad(self):
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), now=NOW)
        block = payload["ties"][0]["players"]["home"]
        squad = {p["player"] for p in block["squad"]}
        on = {p["player"] for line in block["lines"] for p in line}
        assert on <= squad

    def test_a_confirmed_starter_we_hold_nothing_on_joins_the_squad(self):
        # A youth debutant is not in the ranked tables and is on the pitch.
        # He has to reach the squad list too or the pitch cannot place him.
        from types import SimpleNamespace
        spot = lambda n, pos: SimpleNamespace(name=n, position=pos, shirt=None,
                                              detail="", captain=False)
        sheets = {"Arsenal|Arsenal v Wrexham": SimpleNamespace(
            formation=None, starters=["Youth Debutant"],
            spots=[spot("Youth Debutant", "M")], lines=[], bench=[])}
        payload = cups.build([tie("Arsenal", "Wrexham")], history(), {}, {},
                             squads=TestPlayers.squads(), lineups=sheets, now=NOW)
        block = payload["ties"][0]["players"]["home"]
        assert "Youth Debutant" in {p["player"] for p in block["squad"]}
