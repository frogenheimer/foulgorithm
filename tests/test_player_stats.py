"""Per-player foul rates for BOTH divisions, which we were told did not exist.

`features/promotion.py` has said since it was written that "Championship player
data does not exist at any price", and this whole cup build was designed around
that. It was wrong. The Premier League's own API carries ranked player stats
for competition 12 as well as competition 1: fouls, fouls won, tackles, cards,
appearances and minutes, for 681 Championship players.

The shape is the same awkward one docs/02 already describes for the top flight.
These are TOTALS, not per-match rows. A rate is `total / (minutes / 90)`, which
is enough to publish and not enough to train on, and the difference matters
enough that nothing here pretends otherwise.

One sweep per stat covers a whole division, so a cup tie costs no requests at
all beyond the cache.
"""

import pytest

from foulgorithm.sources import player_stats


def entry(player_id, name, club, value, position="M", shirt=8, other_id=None):
    return {
        "owner": {
            # Two id spaces, and only `id` joins to a squad list or a team
            # sheet. Held apart in the fixture so a test can prove which.
            "playerId": float(other_id if other_id is not None else player_id * 7),
            "id": float(player_id),
            "name": {"display": name},
            "info": {"position": position, "shirtNum": float(shirt)},
            "currentTeam": {"name": club, "club": {"name": club, "id": 1.0}},
        },
        "value": float(value),
    }


class FakeApi:
    """Stands in for pulselive, which reaches the network."""

    def __init__(self, pages, rosters=None, staff=None, teams=None,
                 seasons=None, loose=None):
        self.pages = pages          # {(comp, stat): [[entry, ...], ...]}
        # {comp: {club: [player_id]}}. Defaults to "whoever appears in the
        # ranked tables", which is what the old currentTeam route assumed.
        self.rosters = rosters
        self.staff = staff or {}    # {team_id: [name]}, the club's own list
        self.teams = teams or {}    # {comp: [team dict]}
        self.seasons = seasons or {}
        self.loose = loose or {}    # the endpoint that included departed players
        self.calls = []
        self.calls_raw = []

    def squad_ids(self, competition):
        if self.rosters is not None:
            return self.rosters.get(competition, {})
        out = {}
        for (comp, _stat), pages in self.pages.items():
            if comp != competition:
                continue
            for page in pages:
                for e in page:
                    owner = e["owner"]
                    club = (owner.get("currentTeam") or {}).get("name")
                    # `id`, matching the real squad endpoint. See TestIdSpace.
                    out.setdefault(club, set()).add(int(owner["id"]))
        return {k: sorted(v) for k, v in out.items()}

    def _get(self, path):
        self.calls_raw.append(path)
        if path.startswith("competitions/"):
            comp = int(path.split("competitions/")[1].split("/")[0])
            return {"content": [{"id": float(self.seasons.get(comp, 1))}]}
        if path.startswith("teams/") and "staff" in path:
            tid = int(path.split("teams/")[1].split("/")[0])
            return {"players": [
                {"id": float(i + 1), "name": {"display": n}}
                for i, n in enumerate(self.staff.get(tid, []))
            ]}
        if path.startswith("teams?"):
            comp = int(path.split("comps=")[1].split("&")[0])
            return {"content": self.teams.get(comp, [])}
        if path.startswith("players?"):
            tid = int(path.split("teams=")[1].split("&")[0])
            return {"content": [
                {"id": float(i + 1), "name": {"display": n}}
                for i, n in enumerate(self.loose.get(tid, []))
            ]}
        comp = int(path.split("comps=")[1].split("&")[0])
        stat = path.split("ranked/players/")[1].split("?")[0]
        page = int(path.split("page=")[1])
        self.calls.append((comp, stat, page))
        pages = self.pages.get((comp, stat), [])
        content = pages[page] if page < len(pages) else []
        return {"stats": {"content": content,
                          "pageInfo": {"numPages": len(pages) or 1}}}


class TestSweep:
    def test_it_pages_until_the_source_runs_out(self, tmp_path):
        api = FakeApi({(12, "fouls"): [[entry(1, "A", "Wrexham", 10)],
                                       [entry(2, "B", "Wrexham", 5)]]})
        out = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert set(out) == {1, 2}
        assert [c[2] for c in api.calls] == [0, 1]

    def test_values_are_keyed_by_player_id_not_name(self, tmp_path):
        # Two players can share a display name; ids cannot collide, and the
        # team sheets we join against carry ids.
        api = FakeApi({(12, "fouls"): [[entry(1, "Reece James", "Wrexham", 10),
                                        entry(2, "Reece James", "Sheffield Weds", 4)]]})
        out = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert out[1]["value"] == 10 and out[2]["value"] == 4

    def test_each_row_carries_the_club_and_position(self, tmp_path):
        api = FakeApi({(12, "fouls"): [[entry(1, "A", "Wrexham", 10, position="D", shirt=4)]]})
        row = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)[1]
        assert row["club"] == "Wrexham"
        assert row["position"] == "D"
        assert row["shirt"] == 4


class TestSquads:
    """A division's players, with every stat joined onto each."""

    def build(self):
        pages = {}
        for stat, values in (("fouls", {1: 28, 2: 5}),
                             ("was_fouled", {1: 17, 2: 9}),
                             ("total_tackle", {1: 42, 2: 3}),
                             ("yellow_card", {1: 5}),
                             ("appearances", {1: 48, 2: 12}),
                             ("mins_played", {1: 1373, 2: 400})):
            pages[(12, stat)] = [[entry(pid, f"P{pid}", "Wrexham", v)
                                  for pid, v in values.items()]]
        return FakeApi(pages)

    def test_a_club_comes_back_with_its_players(self, tmp_path):
        squads = player_stats.squads("E1", api=self.build(), cache_root=tmp_path)
        assert "Wrexham" in squads
        assert {p.player for p in squads["Wrexham"]} == {"P1", "P2"}

    def test_rates_are_per_ninety_not_totals(self, tmp_path):
        squads = player_stats.squads("E1", api=self.build(), cache_root=tmp_path)
        p = next(p for p in squads["Wrexham"] if p.player == "P1")
        assert p.fouls == 28
        assert p.minutes == 1373
        assert p.fouls_per_90 == pytest.approx(28 / (1373 / 90), abs=0.01)

    def test_a_stat_a_player_never_recorded_is_zero_not_missing(self, tmp_path):
        # Pulselive omits players on zero from a ranked table rather than
        # listing them, so an absent name means zero and not unknown.
        squads = player_stats.squads("E1", api=self.build(), cache_root=tmp_path)
        p = next(p for p in squads["Wrexham"] if p.player == "P2")
        assert p.yellows == 0

    def test_a_player_with_no_minutes_has_no_rate_rather_than_a_zero(self, tmp_path):
        api = self.build()
        api.pages[(12, "mins_played")] = [[entry(1, "P1", "Wrexham", 0)]]
        squads = player_stats.squads("E1", api=api, cache_root=tmp_path)
        p = next(p for p in squads["Wrexham"] if p.player == "P1")
        assert p.fouls_per_90 is None

    def test_thin_evidence_is_flagged_rather_than_hidden(self, tmp_path):
        squads = player_stats.squads("E1", api=self.build(), cache_root=tmp_path)
        p2 = next(p for p in squads["Wrexham"] if p.player == "P2")
        p1 = next(p for p in squads["Wrexham"] if p.player == "P1")
        assert p2.thin is True      # 400 minutes
        assert p1.thin is False     # 1373 minutes

    def test_players_come_back_busiest_first(self, tmp_path):
        squads = player_stats.squads("E1", api=self.build(), cache_root=tmp_path)
        assert [p.player for p in squads["Wrexham"]] == ["P1", "P2"]


class TestDivisions:
    def test_the_premier_league_maps_to_competition_one(self):
        assert player_stats.COMPETITIONS["E0"] == 1

    def test_the_championship_maps_to_competition_twelve(self):
        assert player_stats.COMPETITIONS["E1"] == 12

    def test_a_division_we_do_not_hold_raises_rather_than_guessing(self, tmp_path):
        with pytest.raises(KeyError):
            player_stats.squads("E2", api=FakeApi({}), cache_root=tmp_path)


class TestCache:
    """Fetch once, parse many. The first principle in docs/02.

    A full sweep of both divisions is about 290 requests: the Premier League
    alone is 30 to 36 pages per stat. That is two minutes of round trips for
    numbers that move once a match, so it goes to disk and the site build reads
    the disk.
    """

    def pages(self):
        return FakeApi({(12, "fouls"): [[entry(1, "A", "Wrexham", 10)]]})

    def test_the_first_sweep_hits_the_source_and_writes_a_cache(self, tmp_path):
        api = self.pages()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert len(api.calls) == 1
        assert (tmp_path / "pulselive" / "ranked_12_fouls.json").exists()

    def test_the_second_sweep_reads_the_cache_and_asks_nothing(self, tmp_path):
        api = self.pages()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        api.calls.clear()
        out = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert api.calls == []
        assert out[1]["value"] == 10

    def test_force_refetches_past_the_cache(self, tmp_path):
        api = self.pages()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        api.calls.clear()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path, force=True)
        assert len(api.calls) == 1

    def test_a_cached_sweep_keeps_its_integer_keys(self, tmp_path):
        # JSON has no integer keys. Round-tripping a dict keyed by player id
        # turns every one into a string, and the join to a team sheet is on
        # ints, so it would silently match nothing.
        api = self.pages()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        out = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert all(isinstance(k, int) for k in out)

    def test_a_failed_refetch_leaves_the_usable_cache_alone(self, tmp_path):
        # Stale beats gone, exactly as sources/football_data.fetch decided.
        api = self.pages()
        player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)

        class Broken:
            def _get(self, path):
                raise RuntimeError("source down")

        out = player_stats.sweep(12, "fouls", api=Broken(), cache_root=tmp_path, force=True)
        assert out[1]["value"] == 10


class TestAcrossDivisions:
    """A player's record follows him, not his club's current division.

    Wolves came down and their squad's minutes are Premier League ones. Wrexham
    went up and theirs are Championship ones. Sweeping only the division a club
    is in TODAY gave Wolves seven players with any record at all, which reads
    as a club with no squad rather than as a club whose history is filed
    elsewhere.

    Same rule as the team records: pool both, and label the split. Never pool
    silently.
    """

    def api(self):
        pages = {}
        # Same player id in both divisions: 900 minutes up top, 450 below.
        for comp, mins, fouls in ((1, 900, 18), (12, 450, 12)):
            for stat, val in (("fouls", fouls), ("mins_played", mins),
                              ("appearances", 10), ("was_fouled", 5),
                              ("total_tackle", 7), ("yellow_card", 2),
                              ("red_card", 0)):
                pages[(comp, stat)] = [[entry(1, "Traveller", "Burnley", val)]]
        return FakeApi(pages)

    def test_totals_are_summed_across_both_divisions(self, tmp_path):
        out = player_stats.for_clubs(["Burnley"], api=self.api(), cache_root=tmp_path)
        p = out["Burnley"][0]
        assert p.minutes == 1350
        assert p.fouls == 30

    def test_the_rate_is_over_the_pooled_minutes(self, tmp_path):
        out = player_stats.for_clubs(["Burnley"], api=self.api(), cache_root=tmp_path)
        p = out["Burnley"][0]
        assert p.fouls_per_90 == pytest.approx(30 / (1350 / 90), abs=0.01)

    def test_the_split_is_carried_so_the_page_can_say_where(self, tmp_path):
        out = player_stats.for_clubs(["Burnley"], api=self.api(), cache_root=tmp_path)
        p = out["Burnley"][0]
        assert p.minutes_by_division == {"E0": 900.0, "E1": 450.0}

    def test_the_spell_label_reads_as_english(self, tmp_path):
        out = player_stats.for_clubs(["Burnley"], api=self.api(), cache_root=tmp_path)
        assert out["Burnley"][0].spell_label() == (
            "900 minutes in the Premier League, 450 in the Championship"
        )

    def test_a_one_division_player_says_so_plainly(self, tmp_path):
        api = self.api()
        for stat in player_stats.STATS:
            api.pages.pop((12, stat), None)
        out = player_stats.for_clubs(["Burnley"], api=api, cache_root=tmp_path)
        assert out["Burnley"][0].spell_label() == "900 minutes in the Premier League"

    def test_a_club_we_asked_for_with_nobody_comes_back_empty_not_missing(self, tmp_path):
        out = player_stats.for_clubs(["Wrexham"], api=self.api(), cache_root=tmp_path)
        assert out["Wrexham"] == []

    def test_only_the_clubs_asked_for_come_back(self, tmp_path):
        out = player_stats.for_clubs(["Burnley"], api=self.api(), cache_root=tmp_path)
        assert set(out) == {"Burnley"}

    def test_club_names_are_resolved_to_our_spelling(self, tmp_path):
        # The source says "Wolverhampton Wanderers"; every page here says
        # "Wolves", and the join to a team record is on our spelling.
        pages = {}
        for stat in player_stats.STATS:
            pages[(1, stat)] = [[entry(1, "A", "Wolverhampton Wanderers", 90)]]
        out = player_stats.for_clubs(["Wolves"], api=FakeApi(pages), cache_root=tmp_path)
        assert len(out["Wolves"]) == 1


class TestRoster:
    """Membership comes from the squad list, never from the stat tables.

    `currentTeam` on a ranked row is the player's LAST club, not his present
    one, so reading membership off it put Petr Cech in Arsenal's 2026/27 squad
    seven years after he retired. The squad endpoint is the authority on who is
    actually there; the ranked tables are the authority on what they have done.
    """

    def api(self):
        pages = {}
        for stat in player_stats.STATS:
            pages[(1, stat)] = [[entry(1, "Current Player", "Arsenal", 90),
                                 entry(99, "Petr Cech", "Arsenal", 90)]]
        # The real squad holds only the current player.
        return FakeApi(pages, rosters={1: {"Arsenal": [1]}, 12: {}})

    def test_a_retired_player_is_not_in_the_squad(self, tmp_path):
        out = player_stats.for_clubs(["Arsenal"], api=self.api(), cache_root=tmp_path)
        assert [p.player for p in out["Arsenal"]] == ["Current Player"]

    def test_a_squad_member_with_no_record_still_appears(self, tmp_path):
        # A summer signing with no minutes is in the squad and has nothing to
        # show. That is a real state and must not silently drop him from the XI.
        pages = {stat: None for stat in ()}
        api = FakeApi({(1, s): [[entry(1, "Played", "Arsenal", 90)]] for s in player_stats.STATS},
                      rosters={1: {"Arsenal": [1, 2]}, 12: {}})
        out = player_stats.for_clubs(["Arsenal"], api=api, cache_root=tmp_path)
        assert len(out["Arsenal"]) == 2
        blank = next(p for p in out["Arsenal"] if p.player_id == 2)
        assert blank.minutes == 0 and blank.fouls_per_90 is None


class TestIdSpace:
    """Pulselive carries two player id spaces and only one of them joins.

    Abdul Fatawu is `id=127644` and `playerId=786120`. Squad lists and team
    sheets are keyed on `id`. Keying the stat sweep on `playerId` joined to
    nothing, and the failure mode was silent: every player came back with zero
    minutes, which renders as a squad that has never played rather than as a
    broken join.
    """

    def test_the_sweep_keys_on_the_id_that_squads_use(self, tmp_path):
        api = FakeApi({(12, "fouls"): [[entry(127644, "Abdul Fatawu", "Ipswich", 10,
                                              other_id=786120)]]})
        out = player_stats.sweep(12, "fouls", api=api, cache_root=tmp_path)
        assert 127644 in out
        assert 786120 not in out

    def test_a_squad_joins_to_its_stats(self, tmp_path):
        pages = {(1, s): [[entry(127644, "Abdul Fatawu", "Arsenal", 90, other_id=786120)]]
                 for s in player_stats.STATS}
        api = FakeApi(pages, rosters={1: {"Arsenal": [127644]}, 12: {}})
        out = player_stats.for_clubs(["Arsenal"], api=api, cache_root=tmp_path)
        assert out["Arsenal"][0].minutes == 90


class TestSquadMembership:
    """Nobody who has left the club may ever appear in its squad.

    Three sources look like a squad and two of them are not:

      - `currentTeam` on a ranked row is a player's LAST club, so it puts
        retired players in a current squad. Petr Cech, Arsenal, 2026/27.
      - `players?teams={id}&compSeasons={id}` is everyone registered to the
        club at any point that season: loanees, U21s, and players who have
        since been sold. It put Andy Robertson, Martin Dubravka and Randal
        Kolo Muani in Tottenham's squad.
      - `teams/{id}/compseasons/{id}/staff` is the club's own current list.
        This is the one.

    A wrong name in a squad is worse than a missing one: it prints a real
    player's foul rate under a shirt he will not be wearing.
    """

    def api(self):
        return FakeApi({}, staff={
            21: ["Kinsky", "Udogie", "Porro"],
        }, teams={1: [{"id": 21.0, "name": "Tottenham Hotspur"}]},
           seasons={1: 841},
           # The looser endpoint, which must NOT be the one consulted.
           loose={21: ["Kinsky", "Udogie", "Porro", "Andy Robertson", "Kolo Muani"]})

    def test_membership_comes_from_the_clubs_own_list(self, tmp_path):
        out = player_stats.squad_ids(1, api=self.api(), cache_root=tmp_path)
        assert out["Tottenham Hotspur"] == [1, 2, 3]

    def test_a_departed_player_never_appears(self, tmp_path):
        api = self.api()
        player_stats.squad_ids(1, api=api, cache_root=tmp_path)
        asked = " ".join(api.calls_raw)
        assert "staff" in asked
        # The loose endpoint is the one that carried the departed players.
        assert "players?pageSize" not in asked
