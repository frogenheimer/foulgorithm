# Backtesting

**Status: Proposed**

The backtest is the most important component in the repository. It is the only thing standing between us and confidently shipping a model that does not work.

It gets built **before** any real model, and the baselines get evaluated through it first.

## Protocol

**Walk-forward by matchweek.** For each matchweek `w` in the evaluation period:

1. Set `as_of` to the earliest kickoff in matchweek `w`, minus a configured margin.
2. Build training features using only facts with `known_at <= as_of`.
3. Fit the model on that training set.
4. Predict every eligible entity in matchweek `w`.
5. Score against observed outcomes.
6. Advance.

No refitting on data from week `w` before predicting week `w`. No global scalers fitted across the whole history. No hyperparameters chosen by looking at the full period.

## Two prediction regimes, scored separately

- **Pre-lineup**: predicted with expected minutes from the minutes model. This is what gets published on Thursday or Friday.
- **Post-lineup**: predicted after official lineups are known, roughly an hour before kickoff. Starting probability collapses to a certainty.

These are different products with different accuracy and they must never be pooled in reporting. Reporting post-lineup accuracy while publishing pre-lineup predictions would be a subtler version of the 2025 leakage bug.

## Leakage defences

Three layers, because this is the failure that killed the previous version.

1. **Structural**: feature functions take `as_of` and the frame they receive is pre-filtered by the harness. A model cannot reach past it because models never touch the database.
2. **Instrumented**: in test mode, the frame wrapper records every row id a model reads. If any has `known_at > as_of`, the run fails.
3. **Canary test**: a synthetic dataset where the target is pure noise. Any model scoring better than chance on it is leaking. This runs in CI.

## Metrics

**Probabilistic quality, which is what actually matters**

- **Log loss** per published line. The primary promotion metric.
- **Brier score**, as a secondary check that is less punishing of confident errors.
- **CRPS** for count markets, which scores the whole distribution rather than one threshold.
- **Calibration**: reliability curves and expected calibration error, bucketed by predicted probability. Published on the site.
- **Sharpness**, conditional on calibration. Among calibrated models, the one further from the base rate is more useful.

**Betting quality, reported but never used alone for promotion**

- **Return on investment at fair odds**, meaning against our own prices. Honest about being a self-referential measure.
- **Return against captured bookmaker prices**, only for the subset where we have them.
- **Closing line value**, the difference between the price available when we predicted and the closing price. The fastest honest signal of edge, and it needs far fewer observations than profit does.

**Sample size discipline**

Every reported metric carries a bootstrap confidence interval and an n. A 12% return over 40 bets means nothing and the report should make that obvious rather than let it look like a result.

## Reproducibility

Every run writes a manifest: git sha, model id and version, config hash, snapshot id, date range, random seed, library versions. Runs are replayable from the manifest alone.

Snapshots are frozen parquet files in `data/snapshots/`, created by a `make snapshot` command that dumps the current database state with a content hash. Experiments run against a snapshot, never against a live database, so a backtest run today and the same run next month give identical numbers.

## Market baseline

Where bookmaker prices exist, the harness includes a "market" pseudo-model that simply converts the price to a probability with the margin removed. Beating this is the real bar. Beating the league average is not an achievement.

We will not have this for most player prop history because no free archive of historical player prop odds exists, which is a known limitation recorded in [12-risks-and-open-questions.md](12-risks-and-open-questions.md). Match-level markets from football-data.co.uk give us a partial substitute for validating the approach.

## Reporting

`make backtest` writes a markdown report to `runs/{run_id}/report.md` with a metrics table per model, calibration plots and the biggest misses. The leaderboard goes to `model_runs` in Postgres so the site's model arena can render it.

The report always names its own weaknesses: sample sizes, periods excluded, and any market where the champion beats the baseline by less than its confidence interval.
