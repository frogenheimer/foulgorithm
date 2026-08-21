# Weekly review

**Status: Proposed**

The weekly review is a pipeline stage, not a good intention. If it depends on remembering to look, it will not happen.

## Why it matters most

A prediction system without a feedback loop degrades silently. Sources change format, a referee retires, a tactical trend shifts the league's foul rate, and none of that announces itself. The review is how we notice.

It is also the entire public credibility of the project. Publishing graded results every week, including the bad ones, is the difference between this and a tipster account that quietly deletes losing posts.

## Automated: the Monday job

Runs Monday morning after the weekend's matches settle.

**1. Settle**
Pull final player match stats for every fixture in the review period. Write `outcomes` rows. Any fixture with missing or suspicious stats is flagged rather than graded, and the run reports the gap.

**2. Grade**
Join predictions to outcomes. For every prediction, compute log loss at each line, Brier, CRPS for count markets and simulated return where a price was captured. Write `prediction_grades`. Pre-lineup and post-lineup predictions are graded separately and never pooled.

**3. Recompute rolling diagnostics**
- Calibration curve and expected calibration error over trailing windows
- Hit rate versus predicted probability, bucketed
- Cumulative return with bootstrap confidence intervals
- Per-market and per-model breakdowns
- Closing line value where odds snapshots exist

**4. Detect drift**
Compare this period against the trailing baseline and flag:
- League-wide foul rate moving beyond its historical band
- A model's calibration degrading materially
- Any feature's distribution shifting sharply, which usually means a source changed format rather than that football changed
- Any challenger model beating the champion for a sustained run

**5. Check data health**
Freshness per source, row counts against expectation, unresolved identities, null rates. A dead scraper is the most likely silent failure and this is where it surfaces.

**6. Write and publish**
A `weekly_reviews` row with the numbers and a generated markdown summary, rendered on the site, plus a short Telegram message: record, calibration trend, worst miss, best call, any warnings, and whether a challenger is knocking.

## Manual: the 20 minutes that matter

The job produces facts. A human decides what they mean. Every Monday:

1. Read the summary. Look at the worst misses specifically, not the aggregate. Aggregates hide the interesting failures.
2. Ask whether each big miss was **variance** (a fine prediction that lost) or **a mistake** (a bad prediction). Only mistakes justify changes. Confusing the two and tinkering after every losing week is the most common way to destroy a working model.
3. Log anything learned in `docs/decisions/` if it changes an approach, or in the review notes if it is just an observation.
4. Decide on promotion only when a challenger has beaten the champion over a meaningful sample, never on one week.

## Anti-overfitting discipline

The review exists to catch real degradation, not to invite weekly fiddling.

- No model change on the basis of a single week's results. Ever.
- Promotion needs a walk-forward win over a sustained period, plus equal or better calibration.
- Every change to features or models gets a fresh full backtest, not a spot check on recent weeks.
- The number of times we have looked at recent results and changed something in response is itself a statistic worth keeping honest about, because each look is a chance to fool ourselves.

## Success signal

Positive closing line value on a few hundred graded predictions is a stronger signal of genuine edge than profit is, and it arrives much sooner. Where we lack prices, calibration on a large sample is the substitute.

Neither is available in month one. Until they are, the honest position on the site is "insufficient data", stated plainly.
