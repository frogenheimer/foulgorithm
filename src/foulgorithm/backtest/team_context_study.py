"""C2 stage one gate: does match-store context beat frozen-archive context?

Three variants of the house model, identical in everything except where the
context factors come from, scored on the same player-matches:

| variant | opponent factor | referee factor |
|---|---|---|
| incumbent | player archive | none. Today's live player pipeline |
| store-opponent | match store | none |
| store-both | match store | match store |

Within the evaluation window both sources are contemporaneous, so this
measures the SWAP alone on equal footing. The recency argument, that the
archive froze and the store did not, sits on top of whatever this finds and
is not claimed by it.

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

    store = matches.assign(_date=matches["kickoff_utc"].dt.date)
    keyed = {}
    for row in store.itertuples():
        keyed[(row._date, row.home_team_raw)] = row.referee_raw
        keyed[(row._date, row.away_team_raw)] = row.referee_raw

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
    history = history.assign(_referee=_referee_by_match(history, matches))

    evaluation = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    if evaluation.empty:
        raise ValueError(f"no player-matches at or after {start}")

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    batches = list(evaluation.groupby(week))
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"
    source = MatchContextSource(matches)

    results = []
    for variant in VARIANTS:
        model = (
            pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
        )
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
                if variant == "store-both" and row._referee:
                    referee, _ = source.referee_factor(row._referee, as_of)
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


def report(results: list[ContextResult]) -> str:
    lines = [
        f"{'variant':<16}{'n':>8}{'MAE':>8}{'logloss':>10}{'ECE':>8}"
        f"{'  o0.5':>9}{'o1.5':>8}{'o2.5':>8}",
        "-" * 76,
    ]
    for r in results:
        by = r.log_loss_by_line
        lines.append(
            f"{r.variant:<16}{r.n:>8,}{r.mae:>8.3f}{r.log_loss:>10.4f}{r.ece:>8.4f}"
            f"{by.get(0.5, 0):>9.4f}{by.get(1.5, 0):>8.4f}{by.get(2.5, 0):>8.4f}"
        )
    return "\n".join(lines)


def main() -> None:
    from foulgorithm.store.matches import load_matches
    from foulgorithm.store.players import load_player_matches

    history = load_player_matches()
    matches = load_matches()
    for market in ("player_fouls_committed", "player_fouls_drawn"):
        print(f"\n== {market} ==")
        print(report(run(history, matches, market)))


if __name__ == "__main__":
    main()
