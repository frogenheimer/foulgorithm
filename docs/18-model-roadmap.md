# Model roadmap

**Status: Proposed, 2026-08-22.**

## Are the current models machine learning?

**No. They are statistical models, and the distinction matters.**

Everything running today is hand-specified. A human wrote down the structure and
the data fills in a handful of numbers:

```
expected fouls = player rate per 90        (shrunk, time-decayed)
               × expected minutes / 90
               × opponent factor
               × referee factor
```

The only things actually *fitted* are a per-line calibration shrink, a global
dispersion scale, and one market coefficient. Everything else, the shape of the
formula, which factors exist, how they combine, is a modelling choice made by
hand.

That is closer to actuarial practice or empirical Bayes than to machine
learning. There is no feature matrix, no loss function being minimised over
parameters, nothing learned about which variables matter or how they interact.

**Why this is not a criticism.** At this data size the hand-specified model is
often the right answer, and it beat a naive baseline by 4%. It is also
interpretable end to end, which is why the overconfidence at the 3+ line was
findable at all. A gradient booster would have hidden it.

**Where it costs us.** The model cannot discover interactions. It cannot learn
that a defensive midfielder against a high-take-on winger fouls more than the
two factors multiplied together suggest. Every interaction has to be imagined
by a human and written in.

---

## Alternative model ideas

Ordered by expected value for the effort. Each has a plain-English summary at
the end.

### 1. Gradient boosting with a Poisson objective

**Technical.** LightGBM or XGBoost with `objective="poisson"` over a per-player
per-match feature matrix: shrunk rate, minutes, position, opponent rates,
referee, rest days, venue, market-implied match state, team form. Time-decayed
sample weights. Hyperparameters tuned by Optuna *inside* each walk-forward fold
so tuning never sees the future. Dispersion estimated on held-out folds to turn
the point prediction into a negative binomial.

**Why it might win.** It finds interactions we have not thought of, and it
handles non-linearity in minutes (the relationship between minutes and fouls is
unlikely to be exactly proportional).

**Why it might not.** Roughly 81,000 rows with a low-count target and heavy
noise. Boosters overfit that happily. It would also destroy the interpretability
that let us find the calibration bug.

**Simply:** let the computer find patterns instead of us writing them down. More
powerful, harder to trust, easy to fool itself.

### 2. Hierarchical Bayesian model

**Technical.** PyMC. Fouls modelled as negative binomial with a log-link linear
predictor containing partially-pooled random effects for player, position, team
and referee, plus fixed effects for minutes and venue. Player effects shrink
toward their position, positions toward the league, all estimated jointly rather
than in sequence.

**Why it might win.** This is the *principled* version of what we already do by
hand. Our shrinkage constants (`prior_matches = 6`) are guesses; a hierarchical
model derives the equivalent from the data. It also produces genuine uncertainty
on every parameter, which would let us widen predictions for thin players
instead of applying one global dispersion.

**Why it might not.** Fit time. A walk-forward backtest refitting weekly across
several seasons is expensive, and variational inference trades accuracy for
speed.

**Simply:** the same idea we have now, but the maths decides how much to trust a
small sample instead of us picking a number.

### 3. Count-specific dispersion

**Technical.** Replace the single global `dispersion_scale` with a fitted
function of the expected count, for example a Poisson-Gamma where the shape
parameter varies with the mean. Directly addresses the diagnosed cause of the
3+ overconfidence.

**Why it wins.** It fixes the actual defect rather than patching the symptom,
and it is a small change to existing code.

**Simply:** stop assuming a player expected to foul once has the same
uncertainty shape as one expected to foul three times.

### 4. Joint match model, for combination tickets

**Technical.** Model all players in a match together with a shared match-level
random effect (referee strictness, game tempo). Player counts become correlated
through that shared term, so a combination's probability is the joint
probability rather than a product of marginals.

**Why it wins.** It fixes the caveat currently printed under every combination
ticket. Multiplying marginals understates the true chance because the legs are
positively correlated.

**Simply:** work out the chance of three players all fouling *in the same
match*, rather than pretending the three are unrelated events.

### 5. Two-stage minutes and fouls

**Technical.** Model P(start), then minutes given selection, then fouls given
minutes, propagating uncertainty through all three rather than plugging in a
point estimate for minutes.

**Why it wins.** Minutes are the largest single driver and currently the
crudest part of the model. A player with a 60% chance of starting has a
genuinely bimodal foul distribution, which a point estimate cannot express.

**Simply:** account for the chance he barely plays, instead of assuming he
plays his average.

### 6. Opponent interaction features

**Technical.** Rather than a scalar opponent factor, build matchup features:
the opponent's take-ons attempted, progressive carries and dribble success
against, matched to the player's position. A full-back facing a high-volume
dribbler is a different proposition from the same full-back facing a target man.

**Why it might not.** The take-on data lived on FBref and was deleted in the
January 2026 Opta termination. Would need a new source.

**Simply:** who you are marking matters more than which club you are playing.

### 7. Ensemble

**Technical.** Weighted blend of survivors, weights fitted on held-out
gameweeks. Usually a small but real gain, and it is what the character
framework already resembles without the fitted weights.

**Simply:** average the models that work, weighted by how well they work.

---

## Recommended order

1. **Count-specific dispersion** (3). Small, fixes a known defect, no new data.
2. **Two-stage minutes** (5). Largest driver, currently crudest.
3. **Hierarchical Bayesian** (2). Replaces our guessed constants with derived
   ones and gives per-player uncertainty.
4. **Joint match model** (4). Makes combination tickets honest.
5. **Gradient boosting** (1), as a challenger to see whether the hand-specified
   structure is leaving anything on the table.

Every one goes through the same harness and has to beat the incumbent
out-of-sample. Nothing ships on being more sophisticated.
