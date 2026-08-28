"""Loading both divisions' match history, tagged so nothing pools by accident.

Every row that leaves this loader carries its season and its division. That is
not decoration: `team_record` groups spells by exactly those two fields, and a
row without them would silently merge a Championship season into a Premier
League one, which is the mistake the spell label exists to prevent.
"""

from foulgorithm.stats import history


class FakeSource:
    """Stands in for sources.football_data, which reaches the network."""

    def __init__(self, rows_by_key, fail=()):
        self.rows_by_key = rows_by_key
        self.fail = set(fail)
        self.calls = []

    def fetch(self, season, division="E0"):
        self.calls.append((season, division))
        if (season, division) in self.fail:
            raise RuntimeError(f"{season} {division} is not published yet")
        return (season, division)

    def parse(self, raw):
        return [dict(r) for r in self.rows_by_key.get(raw, [])]


def row(home="Arsenal", away="Chelsea"):
    return {"home_team_raw": home, "away_team_raw": away, "home_fouls": 10, "away_fouls": 12}


class TestLoad:
    def test_every_row_carries_its_season_and_division(self):
        src = FakeSource({("2026-27", "E0"): [row()]})
        rows = history.load(["2026-27"], "E0", source=src)
        assert rows[0]["season"] == "2026-27"
        assert rows[0]["division"] == "E0"

    def test_seasons_are_fetched_from_the_right_division_file(self):
        src = FakeSource({("2026-27", "E1"): [row("Wrexham", "Burnley")]})
        history.load(["2026-27"], "E1", source=src)
        assert src.calls == [("2026-27", "E1")]

    def test_a_season_that_does_not_exist_yet_is_skipped_not_fatal(self):
        # E1 for a season not published is normal in August, and one missing
        # file must not take the whole page down.
        src = FakeSource({("2025-26", "E1"): [row()]}, fail=[("2026-27", "E1")])
        rows = history.load(["2025-26", "2026-27"], "E1", source=src)
        assert len(rows) == 1
        assert rows[0]["season"] == "2025-26"


class TestWindow:
    """Both divisions, always. A club's own record can cross them.

    Burnley played 2025-26 in the Premier League and 2026-27 in the
    Championship. Reading only the division they are in TODAY would silently
    drop a whole season of their record, and the spell label that is supposed
    to expose the crossing would never see it.
    """

    def test_both_division_files_are_read_for_every_season(self):
        src = FakeSource(
            {
                ("2026-27", "E0"): [row()],
                ("2026-27", "E1"): [row("Wrexham", "Burnley")],
            }
        )
        history.window(["2026-27"], source=src)
        assert sorted(src.calls) == [("2026-27", "E0"), ("2026-27", "E1")]

    def test_it_returns_rows_keyed_by_division(self):
        src = FakeSource(
            {
                ("2026-27", "E0"): [row()],
                ("2026-27", "E1"): [row("Wrexham", "Burnley")],
            }
        )
        out = history.window(["2026-27"], source=src)
        assert set(out) == {"E0", "E1"}
        assert out["E1"][0]["home_team_raw"] == "Wrexham"

    def test_pooled_flattens_every_division_into_one_list(self):
        src = FakeSource(
            {
                ("2026-27", "E0"): [row()],
                ("2026-27", "E1"): [row("Wrexham", "Burnley")],
            }
        )
        rows = history.pooled(history.window(["2026-27"], source=src))
        assert len(rows) == 2
        assert {r["division"] for r in rows} == {"E0", "E1"}

    def test_a_relegated_club_keeps_both_of_its_seasons(self):
        from foulgorithm.stats import team_record

        src = FakeSource(
            {
                ("2025-26", "E0"): [row("Burnley", "Arsenal")],
                ("2025-26", "E1"): [],
                ("2026-27", "E0"): [],
                ("2026-27", "E1"): [row("Burnley", "Wrexham")],
            }
        )
        rows = history.pooled(history.window(["2025-26", "2026-27"], source=src))
        rec = team_record.build("Burnley", rows)
        assert rec.matches == 2
        assert rec.crossed_divisions is True
        assert rec.spell_label() == "1 in the Premier League, 1 in the Championship"


class TestSeasonWindow:
    def test_the_default_window_is_this_season_and_last(self):
        assert history.default_seasons(now_year=2026, now_month=8) == ["2025-26", "2026-27"]

    def test_before_august_the_current_season_started_last_year(self):
        assert history.default_seasons(now_year=2027, now_month=3) == ["2025-26", "2026-27"]
