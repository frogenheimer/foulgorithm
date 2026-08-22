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
