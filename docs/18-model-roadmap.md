# Model roadmap

**Status: Decided and shipped, 2026-08-22. Items 8 and 9 added 2026-08-24 after
the data survey in `28-foul-data-sources.md`, and both come before the rest.**

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

**Changed by the 2026-08-24 data work.** Two things, both in its favour.

The training set can now be **485,569 player-matches across six leagues rather
than 81,327 in one**, which is the regime where a hierarchical model earns its
fit time: the whole objection was cost against a thin sample, and the sample is
no longer thin. It also gains a level, league above team, and
`29-why-leagues-differ.md` says that level should be a single multiplicative
intercept rather than a per-position interaction.

Separately, the league API now supplies **twenty seasons of per-player season
totals**, which is a natural prior for a player with little match history and a
better one than his position's mean. A player with 200 league appearances and no
rows in our match archive is currently treated as unknown; he is not.

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

### 8. Pool the other big-five leagues, with a league offset

**Not yet built. The data is verified as obtainable and free.** See
`28-foul-data-sources.md` for how it was checked.

The same archive we already read holds `misc` files for Italy, Spain, Germany,
France and the USA, identical schema, `Fls` and `Fld` per player per match. Six
leagues together is roughly **450,000 player-matches against the 81,000 we use
today**, for five downloads of about 40 MB.

**Why it is not simply "more rows".** Serie A runs 0.972 against England's 1.197
fouls per 90, a 23% gap, while England's own eight-season spread is about 9%. The
league effect is more than twice the season effect, so concatenating the files
would overstate every Italian player by roughly a fifth. Pooled with a fitted
league intercept it is sound, and that is exactly the shape of the hierarchical
model in item 2: league becomes another level above team and position.

**What it buys, in order of value:**

1. **Position and role priors estimated on 5.5x the data.** Every thin player is
   shrunk toward a prior, so the prior's quality sets the floor for a third of
   the league. This is the largest single win available without a paid source.
2. **A record for players who arrived from abroad.** A summer signing from Serie
   A currently has no history and is priced as a generic midfielder. With a
   league offset his Italian record transfers, discounted rather than discarded.
3. **Better dispersion and shrinkage constants**, currently hand-set, estimated
   across far more players.
4. **A test of whether foul propensity is a player trait or a league artefact.**
   If a player's rank within his league survives a move, it is a trait, and that
   is worth knowing before trusting any of the above.

**What it does NOT buy: recency.** All six files froze on the same day in
September 2025. This fixes volume, never staleness. Anyone reaching for it to
solve the eleven-month gap has misread the problem.

**What the data already says about the offset**, explored in
`29-why-leagues-differ.md` and worth reading before building this:

- The gap is **not** explained by how much each league tackles. Correlation
  between fouls and tackles won is −0.135 across leagues and −0.235 within
  England across seasons. Italy tackles less than England and fouls 23% more.
- It is present in **every position**, 16% to 23%, largest for defenders. So a
  single league intercept is likely to be enough and a league-by-position
  interaction probably will not earn its parameters. Test it, do not assume it.
- It should be **multiplicative**, holding proportionally across roles with very
  different base rates.
- The sharpest test available: **a player who changed leagues should keep his
  rank among peers better than he keeps his rate.** If the difference is
  interpretation rather than behaviour, that is what the data will show, and it
  is a cleaner check than any goodness-of-fit number.

**Tests that decide it.** Held-out log loss on English players only, because
that is what we publish. Pooling has to beat the England-only model on England,
not merely fit more data. Two guards worth building at the same time: the league
offsets should come out with Italy above England by something near the 23%
measured here, and a player who moved leagues mid-history should not show a
discontinuity once the offset is applied.

### 9. Team-level features from the live match store

> 📈 **And the data available for it is far larger than this item assumes.**
> `stats/match/{id}` works on historical fixtures, giving about 180 team stats
> per team per match back to 2006/07 for roughly eighteen minutes of fetching.
> We currently hold six. That turns this item from "move two factors onto live
> data" into "model the opponent on how it actually plays". Details in
> `28-foul-data-sources.md`.
>
> ✅ **The offset this item demanded be measured has now been measured.**
> Same competition, same seasons, England only: the league API reads **3.4% to
> 6.4% higher than the FBref archive, every season, never once lower**, averaging
> about 4.6%. Both track identical year-to-year movement, so it is a definitional
> difference between providers rather than an error in either. Any swap that does
> not carry this term moves every published number by roughly five percent for no
> stated reason. Full table in `28-foul-data-sources.md`.


**Not yet built. Costs nothing and uses data already ingested.**

`opponent_factor` and `refereeFactor` are currently computed from the player
history, which stops in September 2025. The same quantities are derivable from
`store/matches.py`, which holds 9,880 matches back to 2000 and is **current
through May 2026** with fouls on every one.

Two of the three inputs to a player prediction would stop being stale. Only the
player's own rate genuinely needs player-level data, which narrows the problem
considerably and should be done before any purchase is considered.

Care needed: the two sources count fouls differently enough to matter, since
they were collected by different providers. The offset has to be measured before
the swap, not assumed to be zero.

## Recommended order

1. **Count-specific dispersion** (3). Small, fixes a known defect, no new data.
2. **Two-stage minutes** (5). Largest driver, currently crudest.
3. **Hierarchical Bayesian** (2). Replaces our guessed constants with derived
   ones and gives per-player uncertainty.
4. **Joint match model** (4). Makes combination tickets honest.
5. **Gradient boosting** (1), as a challenger to see whether the hand-specified
   structure is leaving anything on the table.

Two items were added after the August 2026 data survey and jump most of that
queue, because both are free and both address the largest current weakness,
which is coverage rather than method:

0a. ~~**Team features from the live match store**~~ **SHIPPED 2026-08-24**, the
    opponent factor half of it. Gated by `backtest/team_context_study.py`:
    neutral on equal footing, and under production conditions, a frozen rate
    against a live store, better on both markets with ECE falling 23% on
    committed and 31% on drawn. The referee half was measured to add nothing
    and stays out. See the modelling log, 2026-08-24. Original note below.

    Costs nothing, uses data
    already on disk, and makes two of three prediction inputs current again.
0b. **Pool the other big-five leagues** (8). The data is **now on disk**:
    485,569 player-matches, 8,968 players, six leagues, fetched 2026-08-24. Its
    value is quantified rather than assumed: of the 35 players the site
    currently shows with no record at all, **16 already have one in the pooled
    set**, including Oscar Mingueza at 128 matches in Spain and Borna Sosa at
    110 in Germany. Those records are being thrown away every publish.

0d. ~~**A club-relative prior for promoted-club players**~~ **SHIPPED
    2026-08-24.** Coventry 0.962, Hull 1.024, Ipswich 1.015 against the league
    mean, applied to the position prior and marked in `why` as `priorFrom:
    promoted-club` so the site can show it as an estimate. Original note kept
    below for the reasoning.

    Three quarters of
    a promoted squad has no Premier League record, against three percent of
    Arsenal's, so every Coventry defender is currently priced identically. We
    already hold each promoted club's Championship team foul rate and already
    turn it into a club prior; it is simply never applied to that club's own
    players. Scaling the position average by the club's Championship rate
    relative to the Championship mean distinguishes a disciplined promoted side
    from a dirty one, which is the whole of what can honestly be said about a
    player nobody has seen in this division. Free, uses data on disk.

0c. ~~**A season-total prior for thin players**~~ **SHIPPED 2026-08-24**, and
    it grew into more than a prior: season totals enter the rate as dated
    pseudo-evidence for every player the archive undercovers, which is the C1
    blend of `34-final-plan.md`. Gated by
    `backtest/season_total_study.py`: 78% of the stale-to-oracle log loss gap
    recovered on committed, 87% on drawn, calibration improved. See the
    modelling log, 2026-08-24. Original note kept below.

    Twenty
    seasons of official per-player totals, 2006/07 onward, free. A player with a
    long career and no rows in our match archive is currently priced as his
    position's average. This is the cheapest correction available to the largest
    single input in a prediction.

Every one goes through the same harness and has to beat the incumbent
out-of-sample. Nothing ships on being more sophisticated.
