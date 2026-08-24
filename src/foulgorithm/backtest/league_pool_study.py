"""C3 gate: does pooling six leagues improve predictions about England?

We hold 485,569 player-matches and read 81,327. The other five leagues are
free, already on disk, and cannot simply be concatenated: Serie A runs 23%
above England. `features/league_pool.py` puts them on one scale.

The gate, in advisor 2's words and adopted verbatim into
`docs/34-final-plan.md`: **foreign data is never allowed to improve England
predictions merely by increasing sample size. It must improve England
out-of-sample scoring after all provider and league transformations are
fitted only on permitted historical data.**

So every variant is scored on English player-matches alone, and the league
offsets are refitted inside each fold from rows knowable at that timestamp.
An offset fitted on the whole file would be the leak the harness exists to
catch.

| variant | training history |
|---|---|
| england-only | England, as today |
| pooled-raw | six leagues concatenated, no offset. The mistake, priced |
| pooled-adjusted | six leagues rescaled to England |

`pooled-raw` is there deliberately. If it beats england-only, more rows are
doing the work; if it loses to `pooled-adjusted`, the offset is doing the
work. That separation is what makes the answer interpretable rather than
merely favourable.

Run with:

    python -m foulgorithm.backtest.league_pool_study
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.features import league_pool
from foulgorithm.models import player_models as pm

LINES = (0.5, 1.5, 2.5)
VARIANTS = ("england-only", "pooled-raw", "pooled-adjusted")

EVAL_START = "2024-08-01"
EVAL_END = "2025-02-04"


@dataclass
class PoolResult:
    variant: str
    market: str
    n: int
    mae: float
    log_loss: float
    log_loss_by_line: dict[float, float]
    ece: float
    thin_log_loss: float
    thin_n: int
    #: Per-observation losses, in a fixed order across variants, so two
    #: variants can be compared as a PAIRED difference. Unpaired intervals on
    #: two highly correlated models say almost nothing about which is better.
    losses: np.ndarray | None = None


def paired_difference(
    a: PoolResult, b: PoolResult, n: int = 2000, seed: int = 7
) -> dict:
    """Is `b` better than `a`, on the same observations, beyond noise?

    Both variants score the identical rows in the identical order, so the
    difference is taken per observation before resampling. That matters here:
    the two models agree about almost every prediction, and comparing their
    separate intervals would hide a real, small, consistent gap inside two
    large overlapping ones.
    """
    diff = a.losses - b.losses
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(diff), size=(n, len(diff)))
    means = diff[draws].mean(axis=1)
    lo, hi = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
    return {
        "improvement": float(diff.mean()),
        "lo": lo,
        "hi": hi,
        "clears_zero": lo > 0,
        "n": len(diff),
    }


def _training_frame(variant: str, pool: pd.DataFrame, as_of, stat: str) -> pd.DataFrame:
    """History for one variant, built from rows knowable at `as_of`."""
    visible = pool[pool["known_at"] <= as_of]
    if variant == "england-only":
        return visible[visible["league"] == "ENG"]
    if variant == "pooled-raw":
        return visible
    offsets = league_pool.league_offsets(visible, stat=stat)
    # A league without enough evidence yet to earn an offset is left out
    # rather than assumed English, which is the refusal to_reference enforces.
    return league_pool.to_reference(visible[visible["league"].isin(offsets)], offsets)


def run(
    pool: pd.DataFrame,
    market: str = "player_fouls_committed",
    start: str = EVAL_START,
    end: str = EVAL_END,
    lines: tuple[float, ...] = LINES,
    thin_threshold: float = 10.0,
) -> list[PoolResult]:
    pool = pool.sort_values("kickoff_utc").reset_index(drop=True)
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"

    english = pool[pool["league"] == "ENG"]
    evaluation = english[
        (english["kickoff_utc"] >= pd.Timestamp(start, tz="UTC"))
        & (english["kickoff_utc"] < pd.Timestamp(end, tz="UTC"))
    ]
    if evaluation.empty:
        raise ValueError("no English player-matches in the evaluation window")

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))

    results = []
    for variant in VARIANTS:
        model = (
            pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
        )
        errors: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []
        thin: list[float] = []

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
            model.fit(_training_frame(variant, pool, as_of, stat))

            for row in batch.itertuples():
                rate, effective = model.player_rate(row.player, as_of)
                opp = model.opponent_factor(row.opponent, as_of)
                mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
                dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))

                observed = float(getattr(row, stat))
                errors.append(abs(dist.mean() - observed))
                row_losses = []
                for line in lines:
                    loss = mx.log_loss_at_line(dist, observed, line)
                    line_losses[line].append(loss)
                    row_losses.append(loss)
                    calib.append((dist.prob_over(line), observed > line))
                # Thin players are who the pooled priors are FOR, so they get
                # their own column: a gain concentrated there is the mechanism
                # working, a gain spread evenly is something else.
                if effective < thin_threshold:
                    thin.extend(row_losses)

        all_losses = [v for values in line_losses.values() for v in values]
        results.append(
            PoolResult(
                variant=variant,
                market=market,
                n=len(errors),
                mae=float(np.mean(errors)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
                thin_log_loss=float(np.mean(thin)) if thin else float("nan"),
                thin_n=len(thin) // len(lines),
                losses=np.array(all_losses),
            )
        )
    return results


def report(results: list[PoolResult]) -> str:
    lines = [
        f"{'variant':<18}{'n':>8}{'MAE':>8}{'logloss':>10}{'ECE':>8}"
        f"{'thin n':>9}{'thin logloss':>14}",
        "-" * 75,
    ]
    for r in results:
        lines.append(
            f"{r.variant:<18}{r.n:>8,}{r.mae:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
            f"{r.thin_n:>9,}{r.thin_log_loss:>14.4f}"
        )
    return "\n".join(lines)


def main() -> None:
    from foulgorithm.store.players import load_all_leagues

    pool = load_all_leagues()
    print(f"{len(pool):,} player-matches across {pool['league'].nunique()} leagues\n")

    transfer = league_pool.rank_transfer(pool)
    print(
        f"rank transfer: {transfer['movers']} movers, correlation "
        f"{transfer['rank_correlation']:+.3f}, rate change {transfer['raw_rate_change']:+.4f} "
        f"raw against {transfer['adjusted_rate_change']:+.4f} adjusted"
    )
    print(f"offsets: {({k: round(v, 3) for k, v in sorted(transfer['offsets'].items())})}")

    for market in ("player_fouls_committed", "player_fouls_drawn"):
        print(f"\n== {market}, scored on England only ==")
        results = run(pool, market)
        print(report(results))

        by = {r.variant: r for r in results}
        paired = paired_difference(by["england-only"], by["pooled-adjusted"])
        verdict = "clears zero" if paired["clears_zero"] else "does NOT clear zero"
        print(
            f"\n  pooled-adjusted against england-only, paired over "
            f"{paired['n']:,} observations:\n"
            f"    {paired['improvement']:+.5f} log loss "
            f"[{paired['lo']:+.5f}, {paired['hi']:+.5f}], {verdict}"
        )


if __name__ == "__main__":
    main()
