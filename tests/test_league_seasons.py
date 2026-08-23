"""Twenty seasons of official player stats, fetched once and kept.

The league publishes per-player season totals back to 2006/07, which is eleven
seasons further back than our match archive reaches and covers both of its gaps.
This is the fetcher for them.

Nothing here touches the network. What matters is the shape: a season that comes
back empty must not be written as though it were real, a stat the league does
not carry must not become a silent zero, and every file must record where it
came from so the next person can tell whether it is stale.
"""

import json

import pytest

from foulgorithm.sources import league_seasons as ls


class TestTheStatList:
    def test_the_denominators_are_present(self):
        """A count with no minutes behind it cannot become a rate."""
        assert "mins_played" in ls.STATS
        assert "appearances" in ls.STATS

    def test_both_foul_markets_are_present(self):
        assert "fouls" in ls.STATS
        assert "was_fouled" in ls.STATS

    def test_no_duplicates(self):
        assert len(set(ls.STATS)) == len(ls.STATS)


class TestAssemblingASeason:
    def test_stats_are_joined_per_player(self):
        raw = {
            "fouls": {"A. Semenyo": 73.0, "L. Delap": 72.0},
            "mins_played": {"A. Semenyo": 3000.0, "L. Delap": 2000.0},
        }
        rows = ls.assemble("2024/25", 719, raw)
        by = {r["player"]: r for r in rows}
        assert by["A. Semenyo"]["fouls"] == 73.0
        assert by["A. Semenyo"]["mins_played"] == 3000.0
        assert by["A. Semenyo"]["season"] == "2024/25"

    def test_a_player_missing_from_one_stat_gets_none_not_zero(self):
        """Zero fouls and unrecorded fouls are different facts."""
        raw = {"fouls": {"A": 5.0}, "mins_played": {"A": 900.0, "B": 400.0}}
        by = {r["player"]: r for r in ls.assemble("2024/25", 719, raw)}
        assert by["B"]["fouls"] is None
        assert by["B"]["mins_played"] == 400.0

    def test_every_player_in_any_stat_appears(self):
        raw = {"fouls": {"A": 1.0}, "mins_played": {"B": 90.0}}
        assert {r["player"] for r in ls.assemble("2024/25", 719, raw)} == {"A", "B"}

    def test_an_empty_season_produces_nothing(self):
        assert ls.assemble("2005/06", 1, {"fouls": {}, "mins_played": {}}) == []


class TestProvenance:
    def test_a_written_file_says_where_it_came_from(self, tmp_path):
        rows = [{"player": "A", "season": "2024/25", "fouls": 1.0}]
        path = ls.write_season(tmp_path, "2024/25", 719, rows, ("fouls",))
        held = json.loads(path.read_text())
        assert held["season"] == "2024/25"
        assert held["seasonId"] == 719
        assert held["source"].startswith("http")
        assert held["fetchedAt"]
        assert held["rows"] == 1
        assert held["stats"] == ["fouls"]

    def test_the_row_count_matches_the_rows(self, tmp_path):
        rows = [{"player": f"P{i}"} for i in range(37)]
        path = ls.write_season(tmp_path, "2024/25", 719, rows, ("fouls",))
        held = json.loads(path.read_text())
        assert held["rows"] == len(held["players"]) == 37

    def test_an_empty_season_is_not_written(self, tmp_path):
        """A file of nothing is indistinguishable from a season we never tried."""
        assert ls.write_season(tmp_path, "2005/06", 1, [], ("fouls",)) is None
        assert list(tmp_path.glob("*.json")) == []


class TestSeasonLabels:
    """The current season is labelled in full and every other one is not."""

    def test_a_four_digit_end_year_is_shortened(self):
        assert ls._short("2026/2027") == "2026/27"

    def test_an_already_short_label_is_untouched(self):
        assert ls._short("2024/25") == "2024/25"

    def test_something_unexpected_is_left_alone(self):
        assert ls._short("weird") == "weird"
