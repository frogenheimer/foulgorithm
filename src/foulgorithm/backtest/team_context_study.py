"""C2 stage one gate: does match-store context beat frozen-archive context?

Two questions, and they need different windows, so the study answers both.

**Is the swap itself any better?** Over a window where both sources are
contemporaneous, this measures the swap alone on equal footing:

| variant | opponent factor | referee factor |
|---|---|---|
| incumbent | player archive | none. Today's live player pipeline |
| store-opponent | match store | none |
| store-both | match store | match store |

**Does currency pay?** Equal footing is not the production situation: the
archive froze in September 2025 and the match store did not. So `run_frozen`
reproduces the real one, a year earlier where truth exists, by cutting the
player archive at a freeze date while leaving the match store whole. That
turns "the store is fresher" from an argument into a measurement, which is
what the release gate in docs/34-final-plan.md requires.

Run with:

    python -m foulgorithm.backtest.team_context_study
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.features.team_context import MatchContextSource
from foulgorithm.models import player_models as pm

LINES = (0.5, 1.5, 2.5)
VARIANTS = ("incumbent", "store-opponent", "store-both")


@dataclass
class ContextResult:
    variant: str
    market: str
    n: int
    mae: float
    log_loss: float
    log_loss_by_line: dict[float, float]
    ece: float


def _referee_by_match(history: pd.DataFrame, matches: pd.DataFrame) -> pd.Series:
    """The referee for each player-match row, joined through the match store.

    The archive does not carry referees; the store does. Joined on date and
    the two clubs in fixture spelling, and a row with no join keeps None,
    which the factor turns into 1.0 with zero effective matches: unknown,
    stated as unknown.
    """
    from foulgorithm.features.team_context import fixture_name

    keyed = {}
    for date, home, away, referee in zip(
        matches["kickoff_utc"].dt.date,
        matches["home_team_raw"],
        matches["away_team_raw"],
        matches["referee_raw"],
        strict=True,
    ):
        keyed[(date, home)] = referee
        keyed[(date, away)] = referee

    dates = history["kickoff_utc"].dt.date
    teams = history["team"].map(fixture_name)
    return pd.Series(
        [keyed.get(pair) for pair in zip(dates, teams, strict=True)],
        index=history.index,
    )


def run(
    history: pd.DataFrame,
    matches: pd.DataFrame,
    market: str = "player_fouls_committed",
    start: str = "2024-01-01",
    lines: tuple[float, ...] = LINES,
) -> list[ContextResult]:
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    # Not underscore-prefixed: itertuples silently renames such columns to
    # positional placeholders, which is a crash at best and a wrong join at
    # worst.
    history = history.assign(referee_join=_referee_by_match(history, matches))

    evaluation = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    if evaluation.empty:
        raise ValueError(f"no player-matches at or after {start}")

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"
    source = MatchContextSource(matches)

    results = []
    for variant in VARIANTS:
        model = pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
        errors: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
            model.fit(history[history["known_at"] <= as_of])
            if variant != "incumbent":
                model.use_match_context(source)

            for row in batch.itertuples():
                rate, _ = model.player_rate(row.player, as_of)
                opp = model.opponent_factor(row.opponent, as_of)
                referee = 1.0
                if variant == "store-both" and row.referee_join:
                    referee, _ = source.referee_factor(row.referee_join, as_of)
                mean = max(rate * (row.minutes / 90.0) * opp * referee, 0.02)
                dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))

                observed = float(getattr(row, stat))
                errors.append(abs(dist.mean() - observed))
                for line in lines:
                    line_losses[line].append(mx.log_loss_at_line(dist, observed, line))
                    calib.append((dist.prob_over(line), observed > line))

        all_losses = [v for values in line_losses.values() for v in values]
        results.append(
            ContextResult(
                variant=variant,
                market=market,
                n=len(errors),
                mae=float(np.mean(errors)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
            )
        )
    return results


def run_frozen(
    history: pd.DataFrame,
    matches: pd.DataFrame,
    market: str = "player_fouls_committed",
    freeze: str = "2024-09-14",
    start: str = "2024-10-01",
    end: str = "2025-02-04",
    lines: tuple[float, ...] = LINES,
) -> list[ContextResult]:
    """The production situation: a frozen archive against a live match store.

    The player history is cut at `freeze` for BOTH variants, so the rate is
    equally stale in each and the only difference is where the opponent
    factor comes from. The match store keeps running, exactly as it does
    today. Anything this finds is what currency alone is worth.
    """
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    freeze_at = pd.Timestamp(freeze, tz="UTC")
    frozen = history[history["known_at"] <= freeze_at]

    evaluation = history[
        (history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC"))
        & (history["kickoff_utc"] < pd.Timestamp(end, tz="UTC"))
    ]
    if evaluation.empty:
        raise ValueError("no player-matches in the evaluation window")

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"
    source = MatchContextSource(matches)

    results = []
    for variant in ("frozen-archive", "frozen-rate-live-context"):
        model = pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
        model.fit(frozen)
        if variant != "frozen-archive":
            model.use_match_context(source)

        errors: list[float] = []
        line_losses: dict[float, list[float]] = {line: [] for line in lines}
        calib: list[tuple[float, bool]] = []

        for _, batch in batches:
            as_of = batch["kickoff_utc"].min()
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
            ContextResult(
                variant=variant,
                market=market,
                n=len(errors),
                mae=float(np.mean(errors)),
                log_loss=float(np.mean(all_losses)),
                log_loss_by_line={k: float(np.mean(v)) for k, v in line_losses.items()},
                ece=mx.expected_calibration_error(calib),
            )
        )
    return results


def report(results: list[ContextResult]) -> str:
    lines = [
        f"{'variant':<26}{'n':>8}{'MAE':>8}{'logloss':>10}{'ECE':>8}"
        f"{'  o0.5':>9}{'o1.5':>8}{'o2.5':>8}",
        "-" * 86,
    ]
    for r in results:
        by = r.log_loss_by_line
        lines.append(
            f"{r.variant:<26}{r.n:>8,}{r.mae:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
            f"{by.get(0.5, 0):>9.4f}{by.get(1.5, 0):>8.4f}{by.get(2.5, 0):>8.4f}"
        )
    return "\n".join(lines)


def main() -> None:
    from foulgorithm.store.matches import load_matches
    from foulgorithm.store.players import load_player_matches

    history = load_player_matches()
    matches = load_matches()
    for market in ("player_fouls_committed", "player_fouls_drawn"):
        print(f"\n== {market}: the swap on equal footing ==")
        print(report(run(history, matches, market)))
        print(f"\n== {market}: a frozen archive against a live store ==")
        print(report(run_frozen(history, matches, market)))


if __name__ == "__main__":
    main()
