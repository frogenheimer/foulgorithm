"""Replay a whole season, gameweek by gameweek, and score the five against each other.

The existing harness answers "which model predicts best" in aggregate. This
answers a different and more legible question: **if the five had actually
competed across a season, publishing picks each gameweek, who would have won?**

Protocol per gameweek:
  1. as_of is the first kickoff of that gameweek
  2. every model refits on rows with known_at <= as_of, and nothing else
  3. each picks its five, in temperament, under the equal-risk constraint
  4. the gameweek plays out, picks are graded against what happened
  5. running totals carry forward

This is the same walk-forward discipline as the harness, applied to the product
rather than to the model, so the output is a league table rather than a log loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from foulgorithm.models import calibration
from foulgorithm.models import player_models as pm

PICKS_PER_GAMEWEEK = 5
TARGET_BAND = (0.10, 0.20)


@dataclass
class Standing:
    character: str
    gameweeks: int = 0
    legs: int = 0
    legs_won: int = 0
    slips_won: int = 0
    stake: float = 0.0
    returned: float = 0.0
    history: list[dict] = field(default_factory=list)

    @property
    def leg_rate(self) -> float:
        return self.legs_won / self.legs if self.legs else 0.0

    @property
    def roi(self) -> float:
        return (self.returned - self.stake) / self.stake if self.stake else 0.0


def _gameweeks(history: pd.DataFrame, start: str, end: str | None) -> list[tuple]:
    window = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        window = window[window["kickoff_utc"] <= pd.Timestamp(end, tz="UTC")]
    week = (window["kickoff_utc"] - window["kickoff_utc"].min()).dt.days // 7
    return list(window.groupby(week))


def _candidates(models, batch, as_of, history):
    """Every bettable leg this gameweek, with each character's probability.

    Only players who actually featured are considered, which removes the
    selection question and measures the foul model alone.
    """
    rows = []
    played = batch[batch["minutes"] >= 20]
    for row in played.itertuples():
        probs_by_line: dict[float, dict[str, float]] = {}
        for cid, model in models.items():
            rate, effective = model.player_rate(row.player, as_of)
            opp = model.opponent_factor(row.opponent, as_of)
            mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
            dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))
            for line in (0.5, 1.5, 2.5):
                p = calibration.correct(
                    dist.prob_over(line), "player_fouls_committed", line
                )
                probs_by_line.setdefault(line, {})[cid] = p
        for line, probs in probs_by_line.items():
            rows.append(
                {
                    "player": row.player,
                    "line": line,
                    "probs": probs,
                    "observed": float(row.fouls_committed),
                    "won": float(row.fouls_committed) > line,
                }
            )
    return rows


def _pick(cid: str, candidates: list[dict]) -> list[dict]:
    """Five legs, in temperament, constrained to the target combined band."""
    def preference(row):
        own = row["probs"][cid]
        others = [p for c, p in row["probs"].items() if c != cid]
        edge = own - (sum(others) / len(others))
        if cid == "tayler":
            return own - abs(edge) * 2.0
        if cid == "alan":
            return edge * 3.0
        if cid == "bdog":
            return edge * 4.0
        if cid == "valentina":
            return edge * 1.5 + own * 0.3
        return own * 0.6 + edge

    ranked = sorted(candidates, key=preference, reverse=True)
    chosen, seen, combined = [], set(), 1.0
    for row in ranked:
        if len(chosen) == PICKS_PER_GAMEWEEK:
            break
        if row["player"] in seen:
            continue
        p = row["probs"][cid]
        remaining = PICKS_PER_GAMEWEEK - len(chosen) - 1
        after = combined * p
        # Both bounds. An earlier version checked only the ceiling, so slips
        # drifted far below the band and the competition was not equal-risk at
        # all: Alan's five legs at a claimed 47.6% each combine to 2.4%, not the
        # 10 to 20% the band was supposed to guarantee.
        if after * (0.97**remaining) > TARGET_BAND[1]:
            continue
        if remaining > 0 and after * (0.90**remaining) < TARGET_BAND[0]:
            continue
        chosen.append(row)
        seen.add(row["player"])
        combined = after
    return chosen


def run(
    history: pd.DataFrame,
    start: str = "2024-08-01",
    end: str | None = "2025-06-01",
    min_train: int = 20000,
    stake: float = 1.0,
) -> list[Standing]:
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    models = {cid: pm.build(cid, "player_fouls_committed") for cid in pm.CHARACTER_SETTINGS}
    standings = {cid: Standing(character=cid) for cid in models}

    for _, batch in _gameweeks(history, start, end):
        as_of = batch["kickoff_utc"].min()
        train = history[history["known_at"] <= as_of]
        if len(train) < min_train or len(batch) < 50:
            continue
        for model in models.values():
            model.fit(train)

        candidates = _candidates(models, batch, as_of, history)
        if len(candidates) < 30:
            continue

        for cid, standing in standings.items():
            picks = _pick(cid, candidates)
            if len(picks) < PICKS_PER_GAMEWEEK:
                continue
            won = sum(1 for p in picks if p["won"])
            combined = 1.0
            for p in picks:
                combined *= p["probs"][cid]
            all_won = won == len(picks)

            standing.gameweeks += 1
            standing.legs += len(picks)
            standing.legs_won += won
            standing.slips_won += int(all_won)
            standing.stake += stake
            # Settled at our own fair odds, which is self-referential and
            # labelled as such: we set the price we are paid.
            standing.returned += (stake / combined) if all_won else 0.0
            standing.history.append(
                {
                    "as_of": as_of.isoformat(),
                    "legsWon": won,
                    "slipWon": all_won,
                    "combined": round(combined, 4),
                }
            )

    return sorted(standings.values(), key=lambda s: -s.leg_rate)


def table(standings: list[Standing]) -> str:
    lines = [
        f"{'character':<12}{'GW':>5}{'legs':>7}{'won':>6}{'leg rate':>10}"
        f"{'slips':>7}{'staked':>9}{'returned':>10}{'ROI':>9}",
        "-" * 75,
    ]
    for s in standings:
        lines.append(
            f"{s.character:<12}{s.gameweeks:>5}{s.legs:>7}{s.legs_won:>6}"
            f"{s.leg_rate:>9.1%}{s.slips_won:>7}{s.stake:>9.0f}{s.returned:>10.1f}{s.roi:>+9.1%}"
        )
    return "\n".join(lines)
