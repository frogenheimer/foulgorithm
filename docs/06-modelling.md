# Modelling

**Status: Decided and shipped, 2026-08-22.** (ladder built, champion promoted)

## The contract

Every model implements the same interface. This is what makes experimentation cheap.

```python
class Model(Protocol):
    id: str          # stable, e.g. "shrunk_rate"
    version: str     # bump when behaviour changes
    market: str      # which MarketSpec it serves

    def fit(self, train: FeatureFrame) -> None: ...
    def predict(self, context: FeatureFrame) -> list[Distribution]: ...
```

Two rules make the rest of the system work:

1. **`predict` returns a `Distribution`, never a number.** A distribution exposes `pmf`, `cdf`, `sf`, `mean`, `quantile` and `prob_over(line)`. Every published line and every fair price derives from it. A point estimate cannot be scored properly, cannot be turned into odds and cannot express uncertainty.
2. **`fit` only ever sees rows the harness gave it.** Models do not read the database. The harness controls what data exists, which is how leakage gets prevented centrally rather than trusted to each model author.

Models self-register:

```python
@register
class ShrunkRate:
    id = "shrunk_rate"
    version = "1.0.0"
    market = "player_fouls_committed"
```

`config_hash` is computed from the model's parameters so two runs with different hyperparameters are distinguishable in `model_runs`.

## The ladder

Models get built in this order, and each one has to beat the previous one in the backtest to be promoted. Most projects skip to step 4 and never learn that step 2 was already good enough.

### 1. League average
Every player gets the league mean for his market. Deliberately stupid. Exists to give the metrics a floor and to prove the harness works.

### 2. Shrunken player rate
Player's own per-90 rate shrunk toward his position's mean, with the shrinkage weight proportional to minutes played. Multiply by expected minutes. This is the empirical Bayes fix for the single worst flaw in the 2025 model, which let a player with 4.6 ninety-minute equivalents top the picks on noise.

This baseline is genuinely competitive and it is what everything else must beat.

### 3. Negative binomial GLM
Regression with a log link on the features below. Interpretable, fast, handles overdispersion honestly, and produces a proper distribution rather than a point estimate. `statsmodels` gives us this with confidence intervals we can inspect.

### 4. Gradient boosting with a count objective
LightGBM with Poisson objective, time-decayed sample weights, hyperparameters tuned by Optuna **inside** each walk-forward fold so tuning never sees the future. Converted to a negative binomial by estimating dispersion on held-out folds.

### 5. Hierarchical Bayesian model
PyMC, with partial pooling across players, positions, teams and referees. This is the theoretically correct answer to the small-sample problem: a player with 3 appearances gets pulled toward his position prior exactly as far as his data warrants, with no hand-tuned shrinkage constant.

Cost is fit time, which matters for a walk-forward backtest across 5 seasons. Mitigations are fitting less often than every gameweek and using variational inference if sampling proves too slow.

### 6. Ensemble
Weighted blend of the survivors, weights fitted on held-out gameweeks. Usually a small but real gain.

## Features

All computed as of a timestamp, all derived from facts with `known_at <= as_of`.

**Prior, where a player has no record here**

- A promoted club's players are mostly unseen in this division: Coventry have a
  Premier League record for 7 of 31 and Hull for 8 of 31, against Arsenal's 28
  of 29. Those players take the position prior **scaled by how their club fouled
  in the Championship**, relative to the Championship mean. Currently Coventry
  0.962, Hull 1.024, Ipswich 1.015.
- It scales the position prior rather than replacing it: a defender at a dirty
  promoted club is still a defender.
- Every prediction reports `priorFrom` as one of `own-record`, `position` or
  `promoted-club`, so an estimate never sits beside a measurement looking
  identical. The site marks the third case `est`.
- Second-tier PLAYER data does not exist free anywhere, so this is the most that
  can honestly be said about someone nobody has seen at this level.

**Player form and ability**
- Per-90 rate for the target stat, exponentially time-decayed, shrunk by minutes
- Same for closely related stats (tackles, take-ons attempted, duels)
- Position played, recent rather than nominal
- Career-to-date volume, as a confidence proxy

**Minutes**
- Expected minutes, from a separate model: probability of starting, given recent starts and lineup data, times expected minutes if starting, plus the substitute branch
- Whether the official lineup is confirmed, which collapses the starting probability to 0 or 1

Expected minutes is the highest-leverage feature in the whole system and the 2025 version did not have it at all. A per-90 rate tells you nothing about a bet that settles on one match unless you know how much of that match the player plays.

**Opponent**
- Opponent's take-ons attempted and progressive carries, which drive fouls conceded against
- Opponent's fouls drawn rate, time-decayed
- Positional matchup where identifiable

**Match context**
- Referee effect, partially pooled, never a raw ratio of averages. A referee's raw fouls-per-game is confounded by which teams he was assigned
- Home or away
- Days of rest, and whether either side played midweek European football
- Derby or high-stakes flag, from a maintained list rather than inferred from thin head-to-head samples
- Expected game state, derived from match odds where available: a heavy underdog defends more and fouls more

**Team**
- Team foul rating with exponential time decay, in the style of the Dixon-Coles attack and defence ratings used for goals since 1997

## What the 2025 model did wrong, structurally

Worth keeping visible, because these are easy to drift back into.

| Old approach | Problem | New approach |
|---|---|---|
| Truncated normal on counts | Wrong support, unreliable tails, and the tails are what we bet on | Count distributions, family chosen per market |
| Multipliers stacked multiplicatively | Noise compounds, no shrinkage, each estimated from tiny samples | Joint estimation in one model, partial pooling |
| Referee ratio of averages | Confounded by team assignment | Referee as a pooled effect alongside team effects |
| Variance from concatenating two teams' logs | Includes between-team spread, so the quoted quantiles were wrong | Dispersion estimated by the model, checked on held-out data |
| Per-90 rates with a 2 x 90 minimum | Small-sample noise dominates the rankings | Shrinkage toward position priors, minutes-weighted |
| No minutes model | A per-90 rate does not answer a single-match question | Explicit expected minutes model |

## Promotion

A model becomes champion for a market only when it beats the incumbent on held-out walk-forward data on log loss **and** is at least as well calibrated. A model that wins on returns but is poorly calibrated does not get promoted, because returns over a few hundred bets are mostly noise and calibration is not.

Promotion is a deliberate act: a commit that changes the champion flag, with the `model_runs` id justifying it referenced in the commit message.
