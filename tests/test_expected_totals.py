"""What we said a match would produce, kept after the match is played.

The homepage showed "We said 22" beside "Fouls 10-13", which is the whole
honesty proposition in one line. It read that number off the current board, and
the board only holds fixtures we are predicting now. The moment the pipeline
started predicting the round that is coming rather than the one just played,
every played card lost its claim and the comparison silently disappeared.

A claim made before kickoff has to outlive the round it was made in, so it is
recorded once and never revised.
"""

import pytest

from foulgorithm.store import expected_totals as store


class TestRecording:
    def test_a_total_is_kept(self, tmp_path):
        store.record({"Arsenal v Coventry": 22.4}, "2026-08-21T20:00:00+00:00", tmp_path)
        assert store.load(tmp_path)["Arsenal v Coventry"]["expected"] == 22.4

    def test_the_first_claim_stands(self, tmp_path):
        """Revising it after kickoff would make the comparison worthless."""
        at = "2026-08-21T20:00:00+00:00"
        store.record({"Arsenal v Coventry": 22.4}, at, tmp_path)
        store.record({"Arsenal v Coventry": 30.0}, at, tmp_path)
        assert store.load(tmp_path)["Arsenal v Coventry"]["expected"] == 22.4

    def test_several_fixtures_coexist(self, tmp_path):
        store.record(
            {"A v B": 21.0, "C v D": 24.0}, "2026-08-21T20:00:00+00:00", tmp_path
        )
        assert len(store.load(tmp_path)) == 2

    def test_it_keeps_when_the_claim_was_made(self, tmp_path):
        store.record({"A v B": 21.0}, "2026-08-21T20:00:00+00:00", tmp_path)
        assert store.load(tmp_path)["A v B"]["publishedAt"]

    def test_nothing_to_record_is_safe(self, tmp_path):
        assert store.record({}, "2026-08-21T20:00:00+00:00", tmp_path) == 0

    def test_an_empty_store_reads_as_empty(self, tmp_path):
        assert store.load(tmp_path) == {}

    def test_a_zero_total_is_not_recorded(self, tmp_path):
        """Zero means the board had nobody in it, not that we expect no fouls."""
        store.record({"A v B": 0.0}, "2026-08-21T20:00:00+00:00", tmp_path)
        assert store.load(tmp_path) == {}
