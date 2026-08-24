"""Refitting the published correction, against the model as it is now.

The live correction was fitted against the model before the season-total
blend and the live opponent factors landed, and both improved calibration,
so a correction sized for a worse model now likely over-shrinks. The refit
keeps the same functional form, corrected = base + (raw - base) x shrink,
and these tests pin the fitting arithmetic on planted miscalibration, the
provenance the reference file must now carry, and that the reader still
reads it.
"""

import json

import numpy as np
import pytest

from foulgorithm.backtest import calibration_fit as cf
from foulgorithm.models import calibration


def planted_pairs(shrink: float, base: float = 0.2, n: int = 20000, seed: int = 7):
    """Predictions whose truthful correction is exactly `shrink`.

    Raw probabilities spread around the base; outcomes drawn from the
    corrected probability, so a fitter that recovers `shrink` is reading the
    miscalibration and not the base rate.
    """
    rng = np.random.default_rng(seed)
    raw = np.clip(base + rng.normal(0.0, 0.15, size=n), 0.01, 0.95)
    true = base + (raw - base) * shrink
    outcomes = rng.uniform(size=n) < true
    return [(float(p), bool(y)) for p, y in zip(raw, outcomes, strict=True)]


class TestFittingOneLine:
    def test_planted_overconfidence_is_recovered(self):
        got = cf.fit_line(planted_pairs(shrink=0.8))
        assert got["shrink"] == pytest.approx(0.8, abs=0.03)
        assert got["base"] == pytest.approx(0.2, abs=0.01)
        assert got["n"] == 20000

    def test_a_calibrated_model_fits_to_one(self):
        got = cf.fit_line(planted_pairs(shrink=1.0))
        assert got["shrink"] == pytest.approx(1.0, abs=0.03)

    def test_underconfidence_fits_above_one(self):
        """The live sample hinted the old correction points the wrong way.
        The form can express that: shrink above one pushes probabilities
        AWAY from the base, and the fitter must be able to land there."""
        got = cf.fit_line(planted_pairs(shrink=1.25))
        assert got["shrink"] == pytest.approx(1.25, abs=0.04)

    def test_too_few_pairs_refuses_rather_than_fits_noise(self):
        with pytest.raises(ValueError, match="[0-9]+ pairs"):
            cf.fit_line(planted_pairs(shrink=0.8)[:40])


class TestKeepOrPublishRaw:
    """A correction earns its line or the line is published raw. The refit
    measured two of six fitted corrections hurting held-out predictions,
    and shipping a correction measured to hurt is not on the table."""

    def report(self, raw=(0.40, 0.010), new=(0.40, 0.008)):
        return {"n": 5000, "raw": raw, "old": (0.41, 0.02), "new": new}

    def test_better_on_both_counts_is_kept(self):
        assert gw_decide(self.report(raw=(0.400, 0.010), new=(0.399, 0.008)))

    def test_a_logloss_tie_with_better_ece_is_kept(self):
        assert gw_decide(self.report(raw=(0.4002, 0.0098), new=(0.4003, 0.0087)))

    def test_costing_real_logloss_is_dropped(self):
        assert not gw_decide(self.report(raw=(0.1880, 0.0055), new=(0.1890, 0.0093)))

    def test_worse_calibration_is_dropped_even_at_equal_logloss(self):
        assert not gw_decide(self.report(raw=(0.3719, 0.0107), new=(0.3719, 0.0119)))


def gw_decide(report):
    return cf.decide({"base": 0.2, "shrink": 0.9, "n": 5000}, report)


class TestTheReferenceFile:
    def payload(self):
        return {
            "player_fouls_committed": {
                "0.5": {"base": 0.47, "shrink": 0.95, "n": 9000},
                "1.5": {"base": 0.18, "shrink": 0.90, "n": 9000},
            }
        }

    def test_provenance_is_written_beside_the_corrections(self, tmp_path):
        path = tmp_path / "calibration.json"
        cf.write_reference(self.payload(), path, fit_window=("2022-08-01", "2024-08-01"))
        held = json.loads(path.read_text())
        meta = held["_meta"]
        assert meta["version"] == 2
        assert meta["fittedAt"]
        assert meta["fitWindow"] == ["2022-08-01", "2024-08-01"]
        assert held["player_fouls_committed"]["0.5"]["shrink"] == 0.95

    def test_the_reader_reads_the_new_shape(self, tmp_path, monkeypatch):
        """`calibration.correct` must keep working against a file that now
        carries _meta and per-line n, or the refit bricks the publish run."""
        path = tmp_path / "calibration.json"
        cf.write_reference(self.payload(), path, fit_window=("a", "b"))
        monkeypatch.setattr(calibration, "CALIBRATION", path)
        monkeypatch.setattr(calibration, "_cache", None)
        corrected = calibration.correct(0.30, "player_fouls_committed", 1.5)
        assert corrected == pytest.approx(0.18 + (0.30 - 0.18) * 0.90, abs=1e-9)

    def test_an_unknown_line_still_passes_through(self, tmp_path, monkeypatch):
        path = tmp_path / "calibration.json"
        cf.write_reference(self.payload(), path, fit_window=("a", "b"))
        monkeypatch.setattr(calibration, "CALIBRATION", path)
        monkeypatch.setattr(calibration, "_cache", None)
        assert calibration.correct(0.30, "player_fouls_committed", 3.5) == 0.30
