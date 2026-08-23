"""The prediction store must never lose or duplicate a claim.

These exist because the honesty commitment depends on them: a published
prediction is never edited and never deleted, and a cron firing twice must not
double-count.
"""

import pytest

from foulgorithm.store import predictions as ps


def make(entity="Saka", line=0.5, fixture="Arsenal v Coventry", **kw):
    return ps.Prediction(
        published_at="2026-08-22T10:00:00+00:00",
        kickoff=kw.pop("kickoff", "2026-08-22T14:00:00+00:00"),
        fixture=fixture,
        entity=entity,
        market="player_fouls_committed",
        line=line,
        probability=kw.pop("probability", 0.62),
        model_id="tayler",
        model_version="1.0.0",
        lineup_confirmed=kw.pop("lineup_confirmed", False),
        thin=False,
    )


class TestKey:
    def test_same_claim_has_the_same_key(self):
        assert make().key == make().key

    def test_a_different_probability_does_not_change_identity(self):
        # Re-running with an updated number is the SAME claim, not a new one.
        # Otherwise a rerun silently doubles the record.
        assert make(probability=0.62).key == make(probability=0.71).key

    def test_pre_and_post_lineup_are_different_claims(self):
        # They are different products and are graded separately.
        assert make(lineup_confirmed=False).key != make(lineup_confirmed=True).key

    @pytest.mark.parametrize("field", ["entity", "line", "fixture"])
    def test_changing_what_identifies_it_changes_the_key(self, field):
        other = {"entity": "Rice", "line": 1.5, "fixture": "Hull v Man United"}[field]
        assert make().key != make(**{field: other}).key


class TestAppend:
    def test_writes_then_skips_on_rerun(self, tmp_path):
        first = ps.append([make("Saka"), make("Rice")], tmp_path)
        assert first["written"] == 2 and first["skipped"] == 0

        again = ps.append([make("Saka"), make("Rice")], tmp_path)
        assert again["written"] == 0, "a rerun must not duplicate"
        assert again["skipped"] == 2
        assert len(ps.load_all(tmp_path)) == 2

    def test_new_claims_append_beside_old_ones(self, tmp_path):
        ps.append([make("Saka")], tmp_path)
        ps.append([make("Saka"), make("Odegaard")], tmp_path)
        rows = ps.load_all(tmp_path)
        assert len(rows) == 2
        assert {r["entity"] for r in rows} == {"Saka", "Odegaard"}

    def test_nothing_is_ever_overwritten(self, tmp_path):
        ps.append([make("Saka", probability=0.62)], tmp_path)
        ps.append([make("Saka", probability=0.99)], tmp_path)
        rows = ps.load_all(tmp_path)
        # The original claim survives untouched. We do not get to revise history.
        assert len(rows) == 1
        assert rows[0]["probability"] == 0.62

    def test_rounds_are_separate_files(self, tmp_path):
        ps.append([make(kickoff="2026-08-22T14:00:00+00:00")], tmp_path)
        ps.append([make(kickoff="2026-08-29T14:00:00+00:00")], tmp_path)
        assert len(list(tmp_path.glob("*.jsonl"))) == 2

    def test_empty_input_is_safe(self, tmp_path):
        assert ps.append([], tmp_path)["written"] == 0


class TestDuplicatesWithinOneBatch:
    """The dedupe checked the file and not the batch it was handed.

    A publish run that emitted the same player twice wrote him twice, because
    both copies were absent from the file when the check ran. 148 rows of the
    committed ledger are repeats that arrived this way, and every scheduled run
    added more. Grading joins on the claim, so a repeat is a double-counted bet.
    """

    def test_a_repeated_claim_in_one_call_is_written_once(self, tmp_path):
        result = ps.append([make("Saka"), make("Saka")], tmp_path)
        assert result["written"] == 1, "the same claim twice is still one claim"
        assert result["skipped"] == 1
        assert len(ps.load_all(tmp_path)) == 1

    def test_the_first_copy_is_the_one_kept(self, tmp_path):
        ps.append([make("Saka", probability=0.61), make("Saka", probability=0.99)], tmp_path)
        rows = ps.load_all(tmp_path)
        assert len(rows) == 1
        assert rows[0]["probability"] == 0.61

    def test_distinct_claims_in_one_call_all_survive(self, tmp_path):
        result = ps.append([make("Saka"), make("Saka", line=1.5), make("Rice")], tmp_path)
        assert result["written"] == 3
        assert len(ps.load_all(tmp_path)) == 3

    def test_repeats_across_rounds_do_not_collide(self, tmp_path):
        later = {"kickoff": "2026-08-29T14:00:00+00:00"}
        result = ps.append([make("Saka"), make("Saka"), make("Saka", **later)], tmp_path)
        assert result["written"] == 2, "same claim, different round, is a new claim"


class TestTheCommittedLedger:
    """The real file, not a fixture. A repeat here is a double-counted bet."""

    def test_no_claim_is_recorded_twice(self):
        from collections import Counter

        rows = ps.load_all()
        if not rows:
            pytest.skip("no ledger in this checkout")
        counts = Counter((r["key"], r["kickoff"][:10]) for r in rows)
        repeats = {k: n for k, n in counts.items() if n > 1}
        assert not repeats, f"{sum(n - 1 for n in repeats.values())} duplicate rows"
