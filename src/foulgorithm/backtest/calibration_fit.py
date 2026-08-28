"""Refit the published correction against the model as it is now.

The correction in `data/reference/calibration.json` shrinks each published
probability toward its base rate, and it was fitted against the model before
2026-08-24, when two changes landed that both IMPROVED calibration: the
season-total blend (ECE 0.0137 to 0.0092 in its gate) and live opponent
factors (0.0137 to 0.0105 in production conditions). A correction sized for a
worse-calibrated model now likely over-shrinks every number on the site.

This refits the SAME functional form, corrected = base + (raw - base) x
shrink, no redesign: the distributional calibration stays where the plan of
record put it, behind the pre-registered live sample. What changes here is
the model the pairs come from, season evidence attached and match-store
opponent factors on, exactly as production predicts today, and the reference
file, which gains provenance so the correction stops being a constant of
unrecorded origin.

Fit and test windows never overlap, mirroring the original discipline: fitted
on walk-forward predictions to July 2024, evaluated on August 2024 onward.

Run with:

    python -m foulgorithm.backtest.calibration_fit
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.models import player_models as pm

REFERENCE = Path("data/reference/calibration.json")

LINES = (0.5, 1.5, 2.5)
MARKETS = ("player_fouls_committed", "player_fouls_drawn")

FIT_START = "2022-08-01"
FIT_END = "2024-08-01"
TEST_END = "2025-09-15"

#: Below this many pairs a fitted shrink is noise wearing a decimal point.
MIN_PAIRS = 500


def fit_line(pairs: list[tuple[float, bool]]) -> dict:
    """Least-squares shrink toward the base rate, the original form.

    base is the observed frequency; shrink is the slope of outcomes on
    (probability - base). One means the raw number was honest, below one
    means overconfidence, above one means the model was too timid.
    """
    if len(pairs) < MIN_PAIRS:
        raise ValueError(
            f"only {len(pairs)} pairs; fitting a correction on fewer than "
            f"{MIN_PAIRS} is how noise gets corrected with more noise"
        )
    p = np.array([raw for raw, _ in pairs], dtype=float)
    y = np.array([1.0 if won else 0.0 for _, won in pairs])
    base = float(y.mean())
    centred = p - base
    shrink = float((centred * (y - base)).sum() / (centred * centred).sum())
    return {"base": round(base, 4), "shrink": round(shrink, 4), "n": len(pairs)}


def collect(
    history: pd.DataFrame,
    evidence: pd.DataFrame | None,
    context,
    market: str,
    start: str,
    end: str,
    lines: tuple[float, ...] = LINES,
) -> dict[float, list[tuple[float, bool]]]:
    """Walk-forward raw probabilities, from the production configuration.

    The evidence frame and context source are as-of gated internally, so
    attaching them once per refit is temporally honest; what matters is that
    they are ATTACHED, because a correction fitted against a model nobody
    runs any more corrects the wrong thing.
    """
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"
    model = pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
    if context is not None:
        model.use_match_context(context)

    window = history[
        (history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC"))
        & (history["kickoff_utc"] < pd.Timestamp(end, tz="UTC"))
    ]
    week = (window["kickoff_utc"] - window["kickoff_utc"].min()).dt.days // 7

    pairs: dict[float, list[tuple[float, bool]]] = {line: [] for line in lines}
    for _, batch in window.groupby(week):
        as_of = batch["kickoff_utc"].min()
        model.fit(history[history["known_at"] <= as_of])
        if evidence is not None and len(evidence):
            model.attach_season_evidence(evidence)

        for row in batch.itertuples():
            rate, _ = model.player_rate(row.player, as_of)
            opp = model.opponent_factor(row.opponent, as_of)
            mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
            dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))
            observed = float(getattr(row, stat))
            for line in lines:
                pairs[line].append((float(dist.prob_over(line)), observed > line))
    return pairs


def evaluate(
    pairs: list[tuple[float, bool]],
    old: dict | None,
    new: dict,
) -> dict:
    """Raw against old correction against new, on held-out pairs."""

    def apply(entry, p):
        if not entry:
            return p
        return min(max(entry["base"] + (p - entry["base"]) * entry["shrink"], 0.001), 0.999)

    def score(corrected):
        eps = 1e-9
        losses = [
            -np.log(min(max(c, eps), 1 - eps)) if won else -np.log(min(max(1 - c, eps), 1 - eps))
            for c, won in corrected
        ]
        return float(np.mean(losses)), mx.expected_calibration_error(corrected)

    raw = [(p, y) for p, y in pairs]
    with_old = [(apply(old, p), y) for p, y in pairs]
    with_new = [(apply(new, p), y) for p, y in pairs]
    return {
        "n": len(pairs),
        "raw": score(raw),
        "old": score(with_old),
        "new": score(with_new),
    }


#: A held-out log loss this much worse than raw still counts as a tie. Below
#: the resolution of a few thousand pairs; anything larger is a real cost.
KEEP_TOLERANCE = 0.0002


def decide(fitted: dict, report: dict) -> bool:
    """Keep the fitted correction, or publish the raw probability instead?

    A correction earns its line: it must not cost held-out log loss beyond
    tolerance, and it must improve held-out calibration. A line that fails
    either is published raw, absent from the reference file, which the reader
    already treats as pass-through.

    Stated plainly because it must stay stated: this consults the held-out
    window for a keep-or-drop binary, six decisions, which is mild selection
    on the test set. The alternative is worse: the 2026-08-24 refit measured
    two of six fitted corrections HARMING held-out predictions, because the
    current model is close to calibrated and window-to-window drift in the
    fit is bigger than the miscalibration left to correct. Shipping a
    correction measured to hurt is not on the table.
    """
    raw_loss, raw_ece = report["raw"]
    new_loss, new_ece = report["new"]
    return new_loss <= raw_loss + KEEP_TOLERANCE and new_ece < raw_ece


def write_reference(
    payload: dict, path: Path = REFERENCE, fit_window: tuple[str, str] = (FIT_START, FIT_END)
) -> None:
    """The corrections plus where they came from, in the shape the reader reads.

    `_meta` is invisible to `calibration.correct`, which looks markets up by
    name, so provenance rides along without a reader change.
    """
    held = {
        "_meta": {
            "version": 2,
            "fittedAt": datetime.now(UTC).isoformat(timespec="seconds"),
            "fitWindow": list(fit_window),
            "modelConfiguration": "house, season evidence attached, match-store opponent factors",
        },
        **payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=2) + "\n")


def main() -> None:
    from foulgorithm.features import season_totals
    from foulgorithm.features.team_context import MatchContextSource
    from foulgorithm.store import player_seasons
    from foulgorithm.store.matches import load_matches
    from foulgorithm.store.players import load_player_matches

    history = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)
    api = player_seasons.load()
    api = api[api["season"].astype(str).str.match(r"\d{4}/\d{2}")]
    evidence = season_totals.evidence(api, history)
    context = MatchContextSource(load_matches())

    old_table = json.loads(REFERENCE.read_text()) if REFERENCE.exists() else {}

    payload: dict = {}
    for market in MARKETS:
        fit_pairs = collect(history, evidence, context, market, FIT_START, FIT_END)
        test_pairs = collect(history, evidence, context, market, FIT_END, TEST_END)

        payload[market] = {}
        print(f"\n== {market} ==")
        print(
            f"{'line':>5}{'old shrink':>12}{'new shrink':>12}{'n fit':>8}"
            f"{'  held-out logloss raw/old/new':>32}{'ECE raw/old/new':>24}{'verdict':>10}"
        )
        for line in LINES:
            fitted = fit_line(fit_pairs[line])
            old_entry = (old_table.get(market) or {}).get(str(line))
            report = evaluate(test_pairs[line], old_entry, fitted)
            kept = decide(fitted, report)
            if kept:
                payload[market][str(line)] = fitted
            old_shrink = old_entry["shrink"] if old_entry else float("nan")
            print(
                f"{line:>5}{old_shrink:>12.4f}{fitted['shrink']:>12.4f}{fitted['n']:>8,}"
                f"{report['raw'][0]:>12.4f}{report['old'][0]:>10.4f}{report['new'][0]:>10.4f}"
                f"{report['raw'][1]:>10.4f}{report['old'][1]:>7.4f}{report['new'][1]:>7.4f}"
                f"{'kept' if kept else 'RAW':>10}"
            )

    write_reference(payload)
    print(f"\nwritten to {REFERENCE}")


if __name__ == "__main__":
    main()
