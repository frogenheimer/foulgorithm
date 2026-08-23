"""One player, one row, whatever order his name arrives in.

Wataru Endo appeared on Liverpool's bench twice: once as "Wataru Endo" from
FPL and once as "Endo Wataru" from the team sheet. Ao Tanaka did the same at
Leeds. Both are family-name-first in one source and given-name-first in the
other, which is precisely the case docs/04-identity-resolution.md flags.

The identity resolver already compares names as unordered token sets and gets
this right. The squad assembly did not: it deduped on the normalised STRING, so
two orderings of the same name were two different people.
"""

import pytest

from foulgorithm.publish import player_round


class TestNameKey:
    def test_reversed_orderings_share_a_key(self):
        assert player_round.name_key("Wataru Endo") == player_round.name_key("Endo Wataru")
        assert player_round.name_key("Ao Tanaka") == player_round.name_key("Tanaka Ao")

    def test_accents_do_not_split_a_player(self):
        assert player_round.name_key("Luka Vušković") == player_round.name_key("Luka Vuskovic")

    def test_different_players_keep_different_keys(self):
        assert player_round.name_key("Wataru Endo") != player_round.name_key("Jota Endo")
        assert player_round.name_key("Dan Burn") != player_round.name_key("Dan Burns")

    def test_case_and_punctuation_are_ignored(self):
        assert player_round.name_key("N'Golo Kante") == player_round.name_key("ngolo kante")

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_names_do_not_all_collide_into_one_player(self, blank):
        assert player_round.name_key(blank) == ()


class TestThePublishedSquads:
    """The real file. A duplicate here is a duplicate on the pitch."""

    @staticmethod
    def rows():
        import json
        from pathlib import Path

        path = Path("site/public/data/players.json")
        if not path.exists():
            pytest.skip("nothing published in this checkout")
        return json.loads(path.read_text())["explorer"]["rows"]

    def test_no_player_appears_twice_in_a_fixture(self):
        from collections import defaultdict

        seen = defaultdict(list)
        for r in self.rows():
            seen[(r["fixture"], r["team"], player_round.name_key(r["fullName"]))].append(
                r["fullName"]
            )
        repeats = {k: v for k, v in seen.items() if len(v) > 1}
        assert not repeats, f"same player under two names: {list(repeats.values())[:5]}"

    def test_a_missing_position_always_has_a_reason(self):
        """"?" reaches the bench as a dash, so each one must be explainable.

        The rule, not the count. A single-word team-sheet name ("Beto",
        "Emersonn") cannot be matched to a squad safely: two words of overlap
        are required, which is what stops Danny Ward the goalkeeper inheriting
        Danny Ward the striker's foul rate. Refusing those is the guard working,
        not failing.

        There are exactly two acceptable reasons:

          - A single-word team-sheet name, where matching is refused on purpose.
          - Nobody of that name in FPL at all, which is our only position
            source. Cup opponents from outside the league and academy players
            called up for one night are genuinely not in it.

        Anything else is a real defect.
        """
        from foulgorithm.sources import fpl
        from foulgorithm.publish.player_round import name_key

        in_fpl = {
            name_key(p.name) for side in fpl.current_squads().values() for p in side
        }
        unexplained = [
            r["fullName"]
            for r in self.rows()
            if r["position"] in ("", "?", None)
            and len(name_key(r["fullName"])) >= 2
            and name_key(r["fullName"]) in in_fpl
        ]
        assert not unexplained, (
            f"{len(unexplained)} players are in FPL yet reached the site with no "
            f"position: {unexplained[:6]}"
        )


class TestSurnameFallback:
    """Team sheets use the name a player goes by, FPL uses the formal one.

    "Andy Robertson" and "Andrew Robertson" share only a surname, so the
    two-word rule refuses them. Inside one club's squad a unique surname is
    safe, and it is the same check a person reading a team sheet would make.
    """

    @staticmethod
    def squad(*names):
        from foulgorithm.publish.player_round import name_key

        return {name_key(n): n for n in names}

    def test_a_diminutive_resolves_on_a_unique_surname(self):
        from foulgorithm.publish.player_round import find_squad_member

        by_key = self.squad("Andrew Robertson", "Virgil van Dijk")
        assert find_squad_member(by_key, "Andy Robertson") == "Andrew Robertson"

    def test_a_shared_surname_is_refused(self):
        """The Danny Ward case, which is why the strict rule exists."""
        from foulgorithm.publish.player_round import find_squad_member

        by_key = self.squad("Danny Ward", "Daniel Ward")
        assert find_squad_member(by_key, "D Ward") is None

    def test_an_exact_name_still_wins(self):
        from foulgorithm.publish.player_round import find_squad_member

        by_key = self.squad("Benjamin White", "Ben Whiteman")
        assert find_squad_member(by_key, "Benjamin White") == "Benjamin White"

    def test_an_unknown_player_returns_nothing(self):
        from foulgorithm.publish.player_round import find_squad_member

        assert find_squad_member(self.squad("Andrew Robertson"), "Kylian Mbappe") is None
