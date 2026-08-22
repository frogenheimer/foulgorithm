"""Grading must be honest, complete and non-destructive."""

import pytest

from foulgorithm.review import grade as g


def pred(entity="Saka", line=0.5, p=0.6, model="house", key=None):
    return {
        "key": key or f"{entity}-{line}-{model}",
        "entity": entity,
        "market": "player_fouls_committed",
        "line": line,
        "probability": p,
        "model_id": model,
        "kickoff": "2026-08-22T14:00:00+00:00",
    }


class TestGrade:
    def test_settles_against_the_observed_count(self, tmp_path):
        out = g.grade({("Saka", "player_fouls_committed"): 2.0}, [pred(line=1.5)], tmp_path)
        assert out["graded"] == 1
        assert out["results"][0].won is True

    def test_a_loss_is_recorded_as_a_loss(self, tmp_path):
        out = g.grade({("Saka", "player_fouls_committed"): 0.0}, [pred(line=0.5)], tmp_path)
        assert out["results"][0].won is False

    def test_missing_outcomes_are_counted_not_guessed(self, tmp_path):
        # A silent gap must never look like a clean sheet.
        out = g.grade({}, [pred(), pred("Rice")], tmp_path)
        assert out["graded"] == 0
        assert out["missing_outcome"] == 2

    def test_confident_and_wrong_costs_more_than_unsure_and_wrong(self, tmp_path):
        bold = g.grade({("A", "player_fouls_committed"): 0.0}, [pred("A", p=0.95)], tmp_path)
        meek = g.grade({("B", "player_fouls_committed"): 0.0}, [pred("B", p=0.55)], tmp_path)
        assert bold["results"][0].log_loss > meek["results"][0].log_loss

    def test_regrading_does_not_duplicate(self, tmp_path):
        outcomes = {("Saka", "player_fouls_committed"): 2.0}
        g.grade(outcomes, [pred()], tmp_path)
        g.grade(outcomes, [pred()], tmp_path)
        lines = (tmp_path / "2026-08-22.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1


class TestSummary:
    def test_reports_claimed_against_actual(self, tmp_path):
        # The column that matters: a model saying 90% while 50% happens is
        # overconfident, and a hit-rate table alone would hide it.
        preds = [pred(f"P{i}", p=0.9, key=f"k{i}") for i in range(4)]
        outcomes = {("P0", "player_fouls_committed"): 1.0, ("P1", "player_fouls_committed"): 1.0,
                    ("P2", "player_fouls_committed"): 0.0, ("P3", "player_fouls_committed"): 0.0}
        res = g.grade(outcomes, preds, tmp_path)
        s = g.summarise(res["results"])["house"]
        assert s["claimed"] == pytest.approx(0.9)
        assert s["actual"] == pytest.approx(0.5)
        assert s["gap"] < 0, "overconfidence must show as a negative gap"

    def test_models_are_summarised_separately(self, tmp_path):
        preds = [pred("A", model="alan", key="a"), pred("A", model="tayler", key="t")]
        res = g.grade({("A", "player_fouls_committed"): 1.0}, preds, tmp_path)
        assert set(g.summarise(res["results"])) == {"alan", "tayler"}
