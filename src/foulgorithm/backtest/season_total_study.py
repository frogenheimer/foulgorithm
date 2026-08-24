"""The C1 release gate: how much of a stale year do season totals recover?

The archive froze on 14 September 2025 and the league's season totals are the
only free evidence about player rates since. Whether blending them in helps,
and by how much, is measurable rather than arguable, by simulating the same
situation one year earlier where per-match truth exists:

- the archive is cut at 14 September 2024;
- predictions run over October 2024 to 3 February 2025, the stretch of
  2024/25 the archive actually holds;
- four evidence variants are scored on identical player-matches.

| variant | history | season evidence |
|---|---|---|
| stale | frozen at the cut | none. Today's live situation |
| deep-history | frozen | completed seasons to 2023/24 |
| running-totals | frozen | the above, plus 2024/25 to date |
| oracle | never frozen | none needed. The ceiling |

**The running totals are reconstructed, and that is stated.** We cannot
snapshot backwards, so each week's 2024/25 totals are rebuilt from the
withheld archive rows: what a settle job would have held had it been running,
replaying numbers the league genuinely published at the time. Reconstructed
rows carry `fetchedAt` equal to the prediction timestamp, so the knowability
gate treats them exactly as a live snapshot.

The gate from docs/34-final-plan.md: the blend ships if the variants recover a
material share of the stale-to-oracle gap without hurting calibration, and
the combined model must beat stale BECAUSE it holds new information: on
players the frozen archive already covers completely, blended and stale rates
are identical by construction, which `tests/test_season_totals.py` asserts as
an equality.

Run with:

    python -m foulgorithm.backtest.season_total_study
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.features import season_totals as st
from foulgorithm.models import player_models as pm

FREEZE = pd.Timestamp("2024-09-14", tz="UTC")
EVAL_START = pd.Timestamp("2024-10-01", tz="UTC")
EVAL_END = pd.Timestamp("2025-02-04", tz="UTC")
LINES = (0.5, 1.5, 2.5)

VARIANTS = ("stale", "deep-history", "running-totals", "oracle")


@dataclass
class VariantResult:
    variant: str
    n: int
    mae: float
    log_loss: float
    log_loss_by_line: dict[float, float]
    ece: float


def running_total_frame(withheld: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """The 2024/25 season totals a settle job would have held at `as_of`.

    Built strictly from rows with known_at before the timestamp, in archive
    name space, so identity resolution is exact and the provider is the
    archive itself: no offset applies, which mirrors a real snapshot pair
    where both readings come from the same provider.
    """
    visible = withheld[withheld["known_at"] <= as_of]
    if visible.empty:
        return pd.DataFrame(columns=["player", "season", "mins_played", "fouls", "was_fouled", "fetchedAt"])
    totals = visible.groupby("player").agg(
        mins_played=("minutes", "sum"),
        fouls=("fouls_committed", "sum"),
        was_fouled=("fouls_drawn", "sum"),
    )
    return totals.reset_index().assign(season="2024/25", fetchedAt=as_of.isoformat())


def _evidence_for(
    variant: str,
    api_completed: pd.DataFrame,
    stale_history: pd.DataFrame,
    season_rows: pd.DataFrame,
    as_of: pd.Timestamp,
) -> pd.DataFrame | None:
    if variant in ("stale", "oracle"):
        return None
    if variant == "deep-history":
        return st.evidence(api_completed, stale_history)
    running = running_total_frame(season_rows, as_of)
    frame = pd.concat([api_completed, running], ignore_index=True)
    return st.evidence(frame, stale_history)


def run(
    history: pd.DataFrame,
    api: pd.DataFrame,
    market: str = "player_fouls_committed",
    lines: tuple[float, ...] = LINES,
) -> list[VariantResult]:
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    stale_history = history[history["known_at"] <= FREEZE]
    season_rows = history[(history["season"] == 2025) & (history["known_at"] > FREEZE)]

    evaluation = history[
        (history["kickoff_utc"] >= EVAL_START) & (history["kickoff_utc"] < EVAL_END)
    ]
    if evaluation.empty:
        raise ValueError("no player-matches in the evaluation window")

    api_completed = api[
        api["season"].astype(str).str.match(r"\d{4}/\d{2}")
        & (api["season"].map(lambda s: int(str(s)[:4])) <= 2023)
    ]

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"

    results = []
    for variant in VARIANTS:
        model = pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
        errors: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []

        # The frozen variants never refit: their history does not change, and
        # refitting on it weekly would only burn time. The oracle refits like
        # the real harness does.
        if variant != "oracle":
            model.fit(stale_history)

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
            if variant == "oracle":
                model.fit(history[history["known_at"] <= as_of])
            else:
                evidence = _evidence_for(variant, api_completed, stale_history, season_rows, as_of)
                if evidence is not None:
                    model.attach_season_evidence(evidence)

            for row in batch.itertuples():
                rate, _ = model.player_rate(row.player, as_of)
                opp = model.opponent_factor(row.opponent, as_of)
                mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
                dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))

                observed = float(getattr(row, stat))
                errors.append(abs(dist.mean() - observed))
                for line in lines:
                    line_losses[line].append(mx.log_loss_at_line(dist, observed, line))
                    calib.append((dist.prob_over(line), observed > line))

        all_losses = [v for values in line_losses.values() for v in values]
        results.append(
            VariantResult(
                variant=variant,
                n=len(errors),
                mae=float(np.mean(errors)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
            )
        )
    return results


def report(results: list[VariantResult]) -> str:
    by_name = {r.variant: r for r in results}
    stale, oracle = by_name["stale"], by_name["oracle"]
    gap = stale.log_loss - oracle.log_loss

    lines = [
        f"{'variant':<16}{'n':>8}{'MAE':>8}{'logloss':>10}{'ECE':>8}"
        f"{'  o0.5':>9}{'o1.5':>8}{'o2.5':>8}{'recovered':>11}",
        "-" * 86,
    ]
    for r in results:
        share = (stale.log_loss - r.log_loss) / gap if gap > 0 else float("nan")
        by = r.log_loss_by_line
        lines.append(
            f"{r.variant:<16}{r.n:>8,}{r.mae:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
            f"{by.get(0.5, 0):>9.4f}{by.get(1.5, 0):>8.4f}{by.get(2.5, 0):>8.4f}"
            f"{share:>10.0%}"
        )
    lines.append("")
    lines.append(
        f"stale to oracle gap: {gap:.4f} log loss. 'recovered' is the share of "
        "that gap each evidence variant closes."
    )
    return "\n".join(lines)


def main() -> None:
    from foulgorithm.store import player_seasons
    from foulgorithm.store.players import load_player_matches

    history = load_player_matches()
    api = player_seasons.load()
    for market in ("player_fouls_committed", "player_fouls_drawn"):
        print(f"\n== {market} ==")
        print(report(run(history, api, market)))


if __name__ == "__main__":
    main()
