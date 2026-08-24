"""Do players in one match move together beyond what the model already says?

The direct test advisor 2 asked for, and the reopen tripwire for the shared
match effect. The variance decomposition in `25-match-variance.md` fitted a
shared sd of zero for the house model, but that zero rests on the model's own
conditional variances being right: overstated idiosyncratic variance could
cancel against missing positive covariance and hide a real shared factor.

This study does not route through the decomposition. Each player's residual
is standardised by his own predictive spread, and pairwise products are
averaged within matches: teammates and opponents separately, because a
genuine match effect moves both while a team-level effect moves only one
side. Under independence the average product is zero. If it reads materially
positive, the Poisson-lognormal architecture comes back off the shelf, per
the conditional reopen recorded in `ideas.md`.

The same frame prices the two-leg check: predicted probability of a double
under independence against how often doubles actually land.

Run with:

    python -m foulgorithm.backtest.pairwise_dependence_study
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from foulgorithm.models import player_models as pm


def pairwise_correlation(frame: pd.DataFrame) -> dict:
    """Mean pairwise product of standardised residuals, within matches.

    Standardising by each prediction's own spread makes the products read as
    correlations, and splitting the ledger by side is the diagnostic: a
    shared match factor lifts both numbers together.
    """
    z = (frame["observed"] - frame["predicted_mean"]) / np.sqrt(frame["predicted_var"])
    frame = frame.assign(_z=z)

    teammate_sum = teammate_pairs = 0.0
    opponent_sum = opponent_pairs = 0.0

    for _, match in frame.groupby("match"):
        sides = [group["_z"].to_numpy() for _, group in match.groupby("team")]
        for values in sides:
            n = len(values)
            if n > 1:
                total = values.sum()
                teammate_sum += (total * total - (values * values).sum()) / 2.0
                teammate_pairs += n * (n - 1) / 2.0
        for i in range(len(sides)):
            for j in range(i + 1, len(sides)):
                opponent_sum += sides[i].sum() * sides[j].sum()
                opponent_pairs += len(sides[i]) * len(sides[j])

    return {
        "teammates": float(teammate_sum / teammate_pairs) if teammate_pairs else float("nan"),
        "opponents": float(opponent_sum / opponent_pairs) if opponent_pairs else float("nan"),
        "teammate_pairs": int(teammate_pairs),
        "opponent_pairs": int(opponent_pairs),
    }


def two_leg_check(frame: pd.DataFrame, line: float = 0.5) -> dict:
    """A double priced from independent marginals, against how doubles land.

    Every cross-team pair in every match. `predicted` multiplies the two
    marginal over-probabilities; `observed` is the share of pairs where both
    players actually went over. If observed runs above predicted, tickets
    built under independence are underpriced in exactly the correlated
    matches, which is the practical cost of a shared factor.
    """
    over_prob = []
    for row in frame.itertuples():
        dist = pm.negbin_pmf(row.predicted_mean, max(row.predicted_var, row.predicted_mean * 1.0001))
        over_prob.append(dist.prob_over(line))
    frame = frame.assign(_p=over_prob, _hit=(frame["observed"] > line))

    predicted_sum = observed_sum = pairs = 0.0
    for _, match in frame.groupby("match"):
        sides = [
            (group["_p"].to_numpy(), group["_hit"].to_numpy(dtype=float))
            for _, group in match.groupby("team")
        ]
        for i in range(len(sides)):
            for j in range(i + 1, len(sides)):
                p_i, h_i = sides[i]
                p_j, h_j = sides[j]
                predicted_sum += p_i.sum() * p_j.sum()
                observed_sum += h_i.sum() * h_j.sum()
                pairs += len(p_i) * len(p_j)

    return {
        "line": line,
        "predicted": float(predicted_sum / pairs) if pairs else float("nan"),
        "observed": float(observed_sum / pairs) if pairs else float("nan"),
        "pairs": int(pairs),
    }


def build_frame(
    history: pd.DataFrame,
    market: str = "player_fouls_committed",
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """House-model residuals per player-match over the evaluation window.

    Same protocol as the player harness: refit weekly on what was knowable,
    predict with actual minutes so the foul model is measured alone.
    """
    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    evaluation = history[history["kickoff_utc"] >= pd.Timestamp(start, tz="UTC")]
    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    stat = "fouls_committed" if market.endswith("committed") else "fouls_drawn"

    model = pm.PlayerFoulModel() if stat == "fouls_committed" else pm.PlayerFouledModel()
    rows = []
    for _, batch in evaluation.groupby(week):
        as_of = batch["kickoff_utc"].min()
        model.fit(history[history["known_at"] <= as_of])
        for row in batch.itertuples():
            rate, _ = model.player_rate(row.player, as_of)
            opp = model.opponent_factor(row.opponent, as_of)
            mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
            rows.append(
                {
                    "match": f"{row.kickoff_utc:%Y-%m-%d}|{min(row.team, row.opponent)}|{max(row.team, row.opponent)}",
                    "team": row.team,
                    "predicted_mean": mean,
                    "predicted_var": mean * max(model.dispersion, 1.02),
                    "observed": float(getattr(row, stat)),
                }
            )
    return pd.DataFrame(rows)


def _per_match_terms(frame: pd.DataFrame) -> pd.DataFrame:
    """Each match's contribution to the two correlations, computed once.

    A correlation is a ratio of sums over matches, so the bootstrap only ever
    needs these four numbers per match. Resampling raw rows instead would
    refilter the whole frame a thousand times over.
    """
    z = (frame["observed"] - frame["predicted_mean"]) / np.sqrt(frame["predicted_var"])
    frame = frame.assign(_z=z)

    rows = []
    for match, block in frame.groupby("match"):
        sides = [group["_z"].to_numpy() for _, group in block.groupby("team")]
        mate_sum = mate_pairs = opp_sum = opp_pairs = 0.0
        for values in sides:
            n = len(values)
            if n > 1:
                total = values.sum()
                mate_sum += (total * total - (values * values).sum()) / 2.0
                mate_pairs += n * (n - 1) / 2.0
        for i in range(len(sides)):
            for j in range(i + 1, len(sides)):
                opp_sum += sides[i].sum() * sides[j].sum()
                opp_pairs += len(sides[i]) * len(sides[j])
        rows.append(
            {
                "match": match,
                "mate_sum": mate_sum,
                "mate_pairs": mate_pairs,
                "opp_sum": opp_sum,
                "opp_pairs": opp_pairs,
            }
        )
    return pd.DataFrame(rows)


def bootstrap_interval(
    frame: pd.DataFrame, key: str, n: int = 500, seed: int = 7
) -> tuple[float, float]:
    """95% interval for a correlation, resampling whole matches.

    Matches, not rows: rows within a match are exactly the dependence being
    measured, and resampling them independently would shrink the interval by
    assuming the answer is zero.
    """
    terms = _per_match_terms(frame)
    sums = terms["mate_sum" if key == "teammates" else "opp_sum"].to_numpy()
    pairs = terms["mate_pairs" if key == "teammates" else "opp_pairs"].to_numpy()

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(terms), size=(n, len(terms)))
    stats = sums[draws].sum(axis=1) / np.maximum(pairs[draws].sum(axis=1), 1e-9)
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main() -> None:
    from foulgorithm.store.players import load_player_matches

    history = load_player_matches()
    for market in ("player_fouls_committed", "player_fouls_drawn"):
        frame = build_frame(history, market)
        result = pairwise_correlation(frame)
        legs = two_leg_check(frame)
        lo, hi = bootstrap_interval(frame, "teammates", n=200)
        print(f"\n== {market} ==")
        print(
            f"teammates {result['teammates']:+.4f} [{lo:+.4f}, {hi:+.4f}] "
            f"over {result['teammate_pairs']:,} pairs"
        )
        print(f"opponents {result['opponents']:+.4f} over {result['opponent_pairs']:,} pairs")
        print(
            f"two-leg doubles at 0.5: predicted {legs['predicted']:.4f} "
            f"observed {legs['observed']:.4f} over {legs['pairs']:,} pairs"
        )


if __name__ == "__main__":
    main()
