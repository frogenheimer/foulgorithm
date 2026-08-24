"""Reading twenty seasons of league totals into one tidy table.

One row per player per season, every stat a column. Rates are derived here
rather than in each caller, because a per-90 computed three different ways in
three places is three chances to divide by the wrong denominator.

The validation matters more than the reading. The source that fed this project
sat frozen for eleven months and nothing failed, so a shape change has to
surface at the boundary rather than as a KeyError inside a model.
"""

import json

import pytest

from foulgorithm.store import player_seasons as ps


def season_file(tmp_path, label="2024-25", players=None, **kw):
    payload = {
        "season": label.replace("-", "/"),
        "seasonId": 719,
        "source": "https://example/stats",
        "fetchedAt": "2026-08-24T00:00:00+00:00",
        "stats": ["fouls", "mins_played"],
        "rows": len(players or []),
        "players": players or [],
    }
    payload.update(kw)
    (tmp_path / f"{label}.json").write_text(json.dumps(payload))
    return tmp_path


def player(name="A. Semenyo", **kw):
    base = {"player": name, "season": "2024/25", "seasonId": 719,
            "fouls": 73.0, "mins_played": 3000.0, "appearances": 35.0}
    base.update(kw)
    return base


class TestLoading:
    def test_it_reads_a_season(self, tmp_path):
        season_file(tmp_path, players=[player()])
        d = ps.load(tmp_path)
        assert len(d) == 1
        assert d.iloc[0]["player"] == "A. Semenyo"

    def test_several_seasons_stack(self, tmp_path):
        season_file(tmp_path, "2024-25", [player()])
        season_file(tmp_path, "2023-24", [player(season="2023/24")])
        assert len(ps.load(tmp_path)) == 2

    def test_every_row_carries_when_its_reading_was_taken(self, tmp_path):
        """An in-progress season's totals were knowable only at the moment we
        read them. The evidence builder needs that moment per row, and the
        latest touch wins: a repaired file's values are the repair's reading."""
        season_file(tmp_path, players=[player()])
        assert ps.load(tmp_path).iloc[0]["fetchedAt"] == "2026-08-24T00:00:00+00:00"

    def test_a_repair_moves_the_reading_time_forward(self, tmp_path):
        season_file(
            tmp_path,
            players=[player()],
            repairedAt="2026-08-25T09:00:00+00:00",
        )
        assert ps.load(tmp_path).iloc[0]["fetchedAt"] == "2026-08-25T09:00:00+00:00"

    def test_an_empty_directory_is_an_empty_frame_not_a_crash(self, tmp_path):
        d = ps.load(tmp_path)
        assert len(d) == 0
        assert "player" in d.columns

    def test_a_corrupt_file_is_reported_not_skipped(self, tmp_path):
        (tmp_path / "broken.json").write_text("{not json")
        with pytest.raises(ValueError, match="broken"):
            ps.load(tmp_path)


class TestRates:
    def test_per_ninety_is_derived(self, tmp_path):
        season_file(tmp_path, players=[player(fouls=73.0, mins_played=3000.0)])
        row = ps.load(tmp_path).iloc[0]
        assert row["fouls_per_90"] == pytest.approx(73.0 / (3000 / 90))

    def test_no_minutes_means_no_rate_rather_than_infinity(self, tmp_path):
        season_file(tmp_path, players=[player(fouls=2.0, mins_played=0.0)])
        assert ps.load(tmp_path).iloc[0]["fouls_per_90"] != ps.load(tmp_path).iloc[0]["fouls_per_90"]

    def test_an_unrecorded_count_does_not_become_a_zero_rate(self, tmp_path):
        """None fouls means we were not told, not that he fouled nobody."""
        season_file(tmp_path, players=[player(fouls=None, mins_played=900.0)])
        v = ps.load(tmp_path).iloc[0]["fouls_per_90"]
        assert v != v, "should be NaN, not 0.0"


class TestValidation:
    def test_a_file_missing_the_players_key_is_rejected(self, tmp_path):
        (tmp_path / "bad.json").write_text(json.dumps({"season": "2024/25"}))
        with pytest.raises(ValueError, match="players"):
            ps.load(tmp_path)

    def test_a_row_count_that_disagrees_is_rejected(self, tmp_path):
        """Guards a truncated write, which is silent otherwise."""
        season_file(tmp_path, players=[player()], rows=99)
        with pytest.raises(ValueError, match="rows"):
            ps.load(tmp_path)

    def test_provenance_is_required(self, tmp_path):
        season_file(tmp_path, players=[player()], fetchedAt="")
        with pytest.raises(ValueError, match="fetchedAt"):
            ps.load(tmp_path)
