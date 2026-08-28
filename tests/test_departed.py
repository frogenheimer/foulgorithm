"""A player who left the club must not appear as though he is still at it.

Cristian Romero joined Atletico Madrid and was still listed in Tottenham's
squad table, because that table was built from match history: he played 49
matches for Spurs, so history says Spurs. History is right about the past and
says nothing about who is at the club now.

The split this enforces:

  - **Training** uses everyone who ever played, departed players included.
    Romero's 4,124 minutes are as informative as they ever were.
  - **Selection** uses the current squad only. A prediction about a player at
    another club is not a weak prediction, it is a wrong one.

FPL separates these cases in its status codes and we were collapsing them into
one boolean. "u" means gone, "i" injured, "s" suspended, "d" doubtful. An
injured first-choice centre back is still in the squad; a sold one is not.
"""

import pytest

from foulgorithm.sources import fpl


def player(status="a", name="Cristian Romero", news=""):
    return fpl.SquadPlayer(
        name=name,
        web_name=name.split()[-1],
        team="Spurs",
        position="DEF",
        available=status == "a",
        chance=None,
        news=news,
        minutes=0,
        starts=0,
        status=status,
    )


class TestDeparted:
    def test_a_transferred_player_is_departed(self):
        gone = player("u", news="Has joined Atletico Madrid permanently")
        assert gone.departed

    def test_a_loaned_out_player_is_departed(self):
        assert player("u", news="Has joined Rangers on loan for the season").departed

    @pytest.mark.parametrize("status", ["i", "d", "s"])
    def test_injured_suspended_and_doubtful_are_still_squad_members(self, status):
        sidelined = player(status, news="Groin injury - Unknown return date")
        assert not sidelined.departed, "sidelined is not the same as gone"
        assert not sidelined.available, "still unavailable for selection"

    def test_an_available_player_is_neither(self):
        fit = player("a")
        assert fit.available and not fit.departed

    def test_departed_is_not_inferred_from_availability(self):
        """The old code had only this boolean, which is why the bug existed."""
        assert not player("i").departed
        assert player("u").departed


class TestSelectableSquad:
    def test_departed_players_are_dropped(self):
        squad = [player("a", "Micky van de Ven"), player("u", "Cristian Romero")]
        names = {p.name for p in fpl.at_the_club(squad)}
        assert names == {"Micky van de Ven"}

    def test_injured_players_are_kept(self):
        squad = [player("i", "Dejan Kulusevski"), player("u", "Cristian Romero")]
        assert {p.name for p in fpl.at_the_club(squad)} == {"Dejan Kulusevski"}

    def test_returns_everyone_when_nobody_has_left(self):
        squad = [player("a", "A"), player("d", "B"), player("s", "C")]
        assert len(fpl.at_the_club(squad)) == 3


class TestAgainstTheRealSquads:
    """The live API, so a change in FPL's own encoding surfaces here."""

    def test_departed_players_exist_and_are_a_minority(self):
        squads = fpl.current_squads()
        everyone = [p for side in squads.values() for p in side]
        gone = [p for p in everyone if p.departed]
        assert gone, "no departed players at all suggests the status code stopped parsing"
        assert len(gone) < len(everyone) * 0.2, "too many to be transfers"

    def test_every_departed_player_says_why(self):
        squads = fpl.current_squads()
        gone = [p for side in squads.values() for p in side if p.departed]
        assert all(p.news for p in gone), "a departure with no explanation is a parse error"


class TestSquadTables:
    """What a club's player table is allowed to contain.

    Three groups, three different answers, and the old code gave the same answer
    to all of them by accident:

      - **Departed** (39 across the league). Out. Their history still trains the
        models, they are simply not at the club.
      - **Thin history** (78, Rio Ngumoha among them). In, with the rate flagged.
        A per-90 off half a match is noise, however absence reads as "this player
        does not exist" and that is a worse lie than a flagged number.
      - **No history at all** (207). Counted, not listed. There is no rate to
        show and twenty blank rows per club is not a stats table.
    """

    import pandas as pd

    @staticmethod
    def history(rows):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "player": name, "team": "Tottenham", "minutes": mins,
                    "fouls_committed": f, "fouls_drawn": 1, "yellows": 0,
                    "tackles_won": 1, "position": "DF",
                }
                for name, mins, f in rows
            ]
        )

    def test_a_thin_player_is_listed_and_flagged(self):
        from foulgorithm.publish import teams

        frame = self.history([("Rio Ngumoha", 40, 1), ("Micky van de Ven", 3000, 20)])
        out = {r["player"]: r for r in teams._players(frame, "Tottenham", None)}
        assert "Rio Ngumoha" in out, "a current player must not vanish for lack of minutes"
        assert out["Rio Ngumoha"]["thin"] is True
        assert out["Micky van de Ven"]["thin"] is False

    def test_a_thin_player_still_reports_his_rate(self):
        from foulgorithm.publish import teams

        frame = self.history([("Rio Ngumoha", 45, 1)])
        row = teams._players(frame, "Tottenham", None)[0]
        assert row["foulsPer90"] == 2.0, "flagged, not hidden"

    def test_the_squad_filter_still_applies(self):
        from foulgorithm.publish import teams

        frame = self.history([("Rio Ngumoha", 40, 1), ("Cristian Romero", 4000, 40)])
        out = teams._players(frame, "Tottenham", {"Rio Ngumoha"})
        assert [r["player"] for r in out] == ["Rio Ngumoha"]


class TestNoDepartedPlayerReachesTheSite:
    """The guard. Every published file, checked against the live squad list.

    Three separate paths can put a player on the site (the explorer, the squad
    tables and the matchday sheet) and each had its own idea of who is at a
    club. This asserts the outcome rather than any one path, so a fourth path
    added later is covered without anyone remembering to cover it.
    """

    @staticmethod
    def departed_names():
        from foulgorithm.sources import fpl

        squads = fpl.current_squads()
        return {p.name for side in squads.values() for p in side if p.departed}

    @staticmethod
    def published(name):
        import json
        from pathlib import Path

        path = Path("site/public/data") / name
        return json.loads(path.read_text()) if path.exists() else None

    def test_the_explorer_lists_nobody_who_left(self):
        data = self.published("players.json")
        if not data:
            pytest.skip("nothing published in this checkout")
        gone = self.departed_names()
        named = {r.get("fullName") or r.get("player") for r in data["explorer"]["rows"]}
        assert not (named & gone), f"departed players in the explorer: {named & gone}"

    def test_the_squad_tables_list_nobody_who_left(self):
        data = self.published("teams.json")
        if not data:
            pytest.skip("nothing published in this checkout")
        gone = self.departed_names()
        named = {p["player"] for club in data["table"] for p in club["players"]}
        assert not (named & gone), f"departed players in squad tables: {named & gone}"

    def test_the_cup_squads_list_nobody_who_left(self):
        """The same rule on the cup pages, checked against a DIFFERENT source.

        Cup squads come from the league's own `teams/{id}/compseasons/{id}/staff`
        list; departures here come from FPL. Two independent sources agreeing is
        worth more than either one checking itself.

        Two wrong sources shipped before this existed. `currentTeam` on a ranked
        row is a player's LAST club, which put a retired goalkeeper in a current
        squad. `players?teams=&compSeasons=` is every registration that season,
        which put eight loanees, the U21s and a player since sold to Juventus in
        Tottenham's 66-man "squad". The club's own list is 33 and correct.
        """
        import json
        from pathlib import Path as P

        gone = self.departed_names()
        checked = 0
        for name in ("league-cup.json", "fa-cup.json"):
            path = P("site/public/data") / name
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            named = {
                p["player"]
                for tie in data.get("ties", [])
                for side in ("home", "away")
                for p in (tie.get("players") or {}).get(side, {}).get("squad", [])
            }
            checked += len(named)
            assert not (named & gone), f"departed players in {name}: {named & gone}"
        if not checked:
            pytest.skip("no cup squads published in this checkout")

    def test_history_still_holds_them(self):
        """The other half of the split. Dropping them from training would be the
        opposite mistake, and a worse one: their minutes are real evidence."""
        from foulgorithm.store.players import load_player_matches

        history = load_player_matches()
        assert "Cristian Romero" in set(history["player"]), "training data must keep him"
