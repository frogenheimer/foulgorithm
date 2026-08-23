"""How much of a match's foul total is shared across its players.

`docs/25-match-variance.md` diagnosed a 39% under-dispersion at match level while
player level sits at 1.007, and proposed fitting the shared component rather than
hunting for its cause. This measures it, because a correction shipped on a number
from a document nobody can re-run is a correction nobody can check.

The model, and it is deliberately the simplest thing that could be true:

    X_i | M  ~  NegBin(M * mu_i)          M has mean 1 and variance s^2

M is whatever moved every player in that match together. A referee letting
things run, a derby boiling, a pitch. We do not claim to know which, and the
whole point of estimating M rather than explaining it is that three attempts to
explain it have already failed.

Decomposing the variance of the total T = sum(X_i):

    Var(T)  =  E[Var(T|M)]  +  Var(E[T|M])
            =  E[sum Var(X_i)]  +  s^2 * (sum mu_i)^2

The first term is what the model already believes. Anything left over is s^2,
and if the leftover comes out at or below zero there is no shared factor to find
and nothing should be shipped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from foulgorithm.models import player_models as pm


@dataclass(frozen=True)
class MatchVariance:
    matches: int
    mean_total: float
    predicted_sd: float
    actual_sd: float
    slope: float
    model_variance: float      # what the model thinks a total's variance is
    residual_variance: float   # what it actually is
    shared_sd: float           # s, the per-match multiplier's sd
    note: str


def measure(
    history: pd.DataFrame,
    character: str = "tayler",
    market: str = "player_fouls_committed",
    start: str = "2024-01-01",
    min_train: int = 20000,
) -> MatchVariance:
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    evaluation = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    if evaluation.empty:
        raise ValueError(f"no player-matches at or after {start}")

    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"
    model = pm.build(character, market)

    # There is no match id in the store, and a match is both sides of it, so
    # the key is the kickoff plus the unordered pair of clubs. Keyed on
    # (team, opponent) instead, every match would be counted twice as two
    # eleven-player halves, and a half is not what a match total means.
    evaluation = evaluation.assign(
        match_key=[
            f"{k.isoformat()}|" + "|".join(sorted((str(t), str(o))))
            for k, t, o in zip(
                evaluation["kickoff_utc"], evaluation["team"], evaluation["opponent"]
            )
        ]
    )

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    rows = []

    for _, batch in evaluation.groupby(week):
        as_of = batch["kickoff_utc"].min()
        train = history[history["known_at"] <= as_of]
        if len(train) < min_train:
            continue
        model.fit(train)

        for match_id, players in batch.groupby("match_key"):
            predicted = 0.0
            variance = 0.0
            for row in players.itertuples():
                rate, _ = model.player_rate(row.player, as_of)
                opponent = model.opponent_factor(row.opponent, as_of)
                # Actual minutes, so this measures the foul model and not the
                # minutes model. Mixing the two in would attribute the minutes
                # model's error to a shared match factor that does not own it.
                mean = model._mean_for(rate, float(row.minutes), opponent, 1.0, row.player)
                predicted += mean
                variance += mean * model.dispersion_at(mean)

            rows.append(
                {
                    "match_id": match_id,
                    "predicted": predicted,
                    "variance": variance,
                    "actual": float(players[stat].sum()),
                }
            )

    frame = pd.DataFrame(rows)
    if len(frame) < 30:
        raise ValueError(f"only {len(frame)} matches, too few to measure")

    return decompose(
        frame["predicted"].to_numpy(),
        frame["variance"].to_numpy(),
        frame["actual"].to_numpy(),
    )


def decompose(
    predicted: np.ndarray, variance: np.ndarray, actual: np.ndarray
) -> MatchVariance:
    """Split the error in a match total into what the model expects and what is left.

    Separated from the fitting so it can be tested against data whose answer is
    known in advance. A measurement that decides whether to ship a correction
    needs a canary of its own, and this project has three negative results from
    corrections applied without one.
    """
    predicted = np.asarray(predicted, dtype=float)
    variance = np.asarray(variance, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Slope of actual on predicted. 1.0 means correctly scaled; above 1.0 means
    # every prediction should sit further from the mean than it does.
    slope = float(np.polyfit(predicted, actual, 1)[0])

    residual_variance = float(np.var(actual - predicted, ddof=1))
    model_variance = float(variance.mean())
    mean_total = float(predicted.mean())

    # Whatever the model's own variance does not account for, expressed as a
    # multiplier on the total. At or below zero there is nothing shared to find,
    # and widening the total would make an already-correct spread wrong.
    leftover = residual_variance - model_variance
    shared_sd = float(np.sqrt(leftover) / mean_total) if leftover > 0 else 0.0

    return MatchVariance(
        matches=len(predicted),
        mean_total=round(mean_total, 2),
        predicted_sd=round(float(predicted.std(ddof=1)), 3),
        actual_sd=round(float(actual.std(ddof=1)), 3),
        slope=round(slope, 3),
        model_variance=round(model_variance, 2),
        residual_variance=round(residual_variance, 2),
        shared_sd=round(shared_sd, 4),
        note=(
            "shared_sd is the sd of a per-match multiplier with mean 1. "
            "Zero means the model's own variance already covers what happens."
        ),
    )


def main() -> None:
    from foulgorithm.store.players import load_player_matches

    result = measure(load_player_matches())
    print(f"matches                {result.matches}")
    print(f"mean predicted total   {result.mean_total}")
    print(f"sd of predictions      {result.predicted_sd}")
    print(f"sd of outcomes         {result.actual_sd}")
    print(f"regression slope       {result.slope}   (1.0 is correctly scaled)")
    print(f"model's own variance   {result.model_variance}")
    print(f"actual residual var    {result.residual_variance}")
    print(f"shared multiplier sd   {result.shared_sd}")
    print()
    print(result.note)


if __name__ == "__main__":
    main()
