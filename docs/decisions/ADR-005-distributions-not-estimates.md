# ADR-005 — Models return distributions, not point estimates

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Every model implements `predict` returning a `Distribution` object exposing `pmf`, `cdf`, `sf`, `mean`, `quantile` and `prob_over(line)`. No model returns a bare number, and no model is trained to predict a single line.

## Context

The 2025 version ranked players by expected fouls. A ranking answers "who fouls most", which every bookmaker already knows. It cannot answer "what is the probability of 2 or more", which is the only question a price can be compared against.

The alternative trap is training a classifier per line. That produces answers across lines that can contradict each other, cannot price a line it was not trained on, and multiplies the number of models by the number of lines.

## Options considered

**Point estimates plus an assumed distribution at read time.** Convenient, and it hides the most important modelling choice (the distribution family and its dispersion) behind an assumption made far from the model. This is close to what the 2025 version did by bolting a truncated normal onto a mean, and it produced quantiles that were wrong.

**One binary classifier per line.** Rejected for the reasons above.

**A distribution per prediction.** Chosen. One fit answers every line, prices are internally consistent, and proper scoring rules like CRPS become available.

## Consequences

- Every market must declare a distribution family, which forces the useful question of whether it is a count or a binary outcome. Cards turn out to be binary, which a count model would have handled badly.
- Storage is a probability mass function per prediction rather than a number. At these volumes that is trivial.
- The site's interactive line explorer becomes almost free, because the full distribution is already there to render.
- Model authors have slightly more work: a gradient booster predicting a mean needs a dispersion estimate to become a distribution. Accepted, and it is the right work to do.
