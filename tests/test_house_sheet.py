"""The house sheet: the model's own flat shouts for one fixture, no
character attached. Grouped by line and market, three players each, the 3+
group only when somebody actually prices there, and three tiers, safe,
optimistic and rogue, one per line, badged safest first and never repeating
a player: Sangare at 1+ AND 2+ is one opinion dressed as two."""

from foulgorithm.publish import player_round


def player(name, committed, drawn):
    return {
        "player": name,
        "fullName": f"Full {name}",
        "committed": {f"p{n}plus": p for n, p in zip((1, 2, 3), committed)},
        "drawn": {f"p{n}plus": p for n, p in zip((1, 2, 3), drawn)},
    }


def fixture(players):
    return {"home": "A", "away": "B", "teams": {"A": players, "B": []}}


class TestHouseSheet:
    PLAYERS = [
        player("Sangare", (0.73, 0.41, 0.22), (0.30, 0.10, 0.02)),
        player("Anderson", (0.68, 0.36, 0.15), (0.40, 0.15, 0.03)),
        player("Tanaka", (0.61, 0.30, 0.10), (0.64, 0.33, 0.08)),
        player("Aina", (0.35, 0.12, 0.03), (0.58, 0.28, 0.06)),
    ]

    def test_groups_hold_the_top_three_by_the_house_price(self):
        sheet = player_round._house_sheet(fixture(self.PLAYERS))
        one_plus = next(
            g for g in sheet["groups"] if g["market"] == "committed" and g["line"] == 1
        )
        assert [p["player"] for p in one_plus["picks"]] == ["Sangare", "Anderson", "Tanaka"]
        assert one_plus["picks"][0]["outOf100"] == 73

    def test_three_plus_only_when_somebody_prices_there(self):
        sheet = player_round._house_sheet(fixture(self.PLAYERS))
        lines = {(g["market"], g["line"]) for g in sheet["groups"]}
        assert ("committed", 3) in lines      # Sangare prices 22/100
        assert ("drawn", 3) not in lines      # best is 8/100, below the floor

    def test_tiers_badge_safest_first_and_a_player_once(self):
        sheet = player_round._house_sheet(fixture(self.PLAYERS))
        tiers = {
            (g["market"], g["line"]): next((p["player"] for p in g["picks"] if p.get("tier")), None)
            for g in sheet["groups"]
        }
        names = [p["player"] for g in sheet["groups"] for p in g["picks"] if p.get("tier")]
        assert len(names) == len(set(names))
        # SAFE is the 1+ tier and it is badged first in both markets, so the
        # best names anchor the safe calls; the later tiers fall to the next.
        assert tiers[("committed", 1)] == "Sangare"
        assert tiers[("drawn", 1)] == "Tanaka"
        assert tiers[("committed", 2)] == "Anderson"
        assert tiers[("drawn", 2)] == "Aina"
        # Every 3+ name is already badged, so the rogue tier is honestly empty.
        assert tiers[("committed", 3)] is None

    def test_tier_names_follow_the_line(self):
        sheet = player_round._house_sheet(fixture(self.PLAYERS))
        for g in sheet["groups"]:
            for p in g["picks"]:
                if p.get("tier"):
                    assert p["tier"] == {1: "safe", 2: "optimistic", 3: "rogue"}[g["line"]]
                    assert p["star"] is True

    def test_at_most_one_badge_per_group(self):
        sheet = player_round._house_sheet(fixture(self.PLAYERS))
        for g in sheet["groups"]:
            assert sum(1 for p in g["picks"] if p.get("tier")) <= 1
