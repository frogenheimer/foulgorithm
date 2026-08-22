# Modelling log

**Append-only.** Newest entry at the top. Never edit or delete an entry: if something turns out to be wrong, write a new entry saying so and link back. The value of this file is seeing what we believed at the time and why we changed our minds.

Every modelling decision lands here: what was tried, what the numbers were, what we concluded and what we are unsure about. A result with no reasoning recorded may as well not have happened, because in three months nobody will remember why the model looks the way it does.

## What goes in an entry

```
## YYYY-MM-DD — Short title

**Question**   What we were trying to find out.
**Method**     What we ran. Enough detail to repeat it.
**Result**     The numbers. With sample sizes.
**Conclusion** What we now believe.
**Caveats**    What would change our mind, and what we did not test.
```

---

## 2026-08-22 — Cards are close to unpredictable, and fouls do not help

**Question.** Cards are the only market where real bookmaker odds exist to check
against, so a model for them is disproportionately valuable. Can we build one?

**Method.** Three variants over 11,789 walk-forward predictions from 2024:
the player's own booking record, expected fouls converted through the league
fouls-per-card ratio, and a blend. Scored against a league base rate.

**Result.**

| variant | says | happens | log loss | ECE |
|---|---|---|---|---|
| own record only | 0.127 | 0.156 | **0.4314** | 0.0327 |
| *league base rate* | 0.138 | 0.156 | *0.4336* | |
| blend | 0.122 | 0.156 | 0.4347 | 0.0341 |
| expected fouls only | 0.116 | 0.156 | 0.4556 | 0.0392 |

**Conclusion, and it is not the one I expected.**

**Cards are close to unpredictable at player level with what we hold.** The best
version beats a model knowing only the league average by **0.5%**. Player fouls,
which beat their own baseline by 4%, look strong by comparison.

**Using expected fouls to predict cards makes it worse.** The mechanism seemed
obvious: a booking usually IS one of the player's fouls. But a foul-heavy player
is not proportionally more bookable. The most plausible reading is that referees
book for the KIND of foul, tactical, reckless, dissent, rather than for the
count, and our data has no notion of kind at all. `foul_weight` now defaults to
zero.

Position priors are real and large, which is the one encouraging part:
defensive midfielders are booked in 21.5% of appearances against 13.9% league
wide. But knowing a player's position is most of what we know.

**This matters beyond cards.** It was the market where we could finally have
measured ourselves against real prices. A model 0.5% better than the base rate
will not survive a bookmaker's margin, so that validation route is effectively
closed too.

**Caveats.** Every variant understates, saying about 12% where 15.6% happens,
consistent with cards having risen 16.3% since 2000 while fouls fell. A shorter
half-life might recover some of that and has not been tried. And "was he booked"
may simply be the wrong question: a model of DISCIPLINARY RISK combining fouls,
tackles and match context could do better than one predicting the card directly.

## 2026-08-22 — The dispersion was wrong, but not for the reason I thought

**Question.** The model overstates the 3+ line. The stated hypothesis was that a
single global dispersion applied the same relative spread to a player expected
to commit 0.3 fouls and one expected 2.5, making the tail too fat for the
former. Is that right?

**Method.** Three steps, in order.

1. Fitted a count-dependent dispersion, slope estimated from quintiles of player
   rate, and measured the effect on bias.
2. Checked whether the negative binomial family fits the observed tail at all.
3. Swept the dispersion VALUE across 8,464 walk-forward predictions.

**Result 1: the hypothesis was wrong.** The fitted slope came out at 0.014, and
bias at the 3+ line moved from -0.0149 to -0.0145. That is noise. Count-dependent
dispersion does essentially nothing here, and the code has been deleted rather
than left in place looking like it works.

**Result 2: the family is right.** Fitted to 59,649 player-matches of 60+
minutes:

| k | actual | negative binomial | Poisson |
|---|---|---|---|
| 0 | 0.4562 | 0.4490 | 0.4138 |
| 3+ | **0.0782** | **0.0760** | 0.0600 |

The negative binomial reproduces the observed 3+ rate to within 3%. A Poisson
understates it by 23%. So the shape was never the problem.

**Result 3: the VALUE was the problem.** Swept against held-out predictions:

| dispersion | bias 0.5 | bias 1.5 | bias 2.5 | total |
|---|---|---|---|---|
| 1.00 | -0.0087 | -0.0087 | -0.0075 | 0.0249 |
| **1.05** | **-0.0021** | **-0.0091** | **-0.0101** | **0.0214** |
| 1.15 | +0.0103 | -0.0095 | -0.0148 | 0.0346 |
| 1.21 | +0.0173 | -0.0095 | -0.0173 | 0.0441 |

**Conclusion.** We were using something close to the population's
variance-to-mean ratio of 1.21. That is the wrong quantity: **the population
ratio includes the spread BETWEEN players, which the model already explains
through each player's own rate.** What is left over, the residual, is far
tighter, and the sweep puts it at about 1.05.

This is the same error as the match-total dispersion bug in a different costume.
Both times the marginal variance was mistaken for the residual variance, and
both times it made the model hedge.

**Also re-fitted the calibration correction on held-out seasons.** It was
previously fitted on the same data it was judged against, which flattered it.
Fitted on 2022-2024, tested on 2024 onward:

| line | raw bias | corrected |
|---|---|---|
| 0.5 | -0.0021 | -0.0025 |
| 1.5 | -0.0077 | -0.0065 |
| 2.5 | **-0.0101** | **-0.0079** |

Fouls drawn came back with a shrink of 1.039 at the 3+ line, slightly above one,
meaning that market was mildly UNDER-confident. The fit is finding real
structure rather than shrinking everything toward the mean by reflex.

**Caveats.** A residual bias of -0.008 at the 3+ line survives both fixes and is
unexplained. It is small, and it is in the direction that overstates, which is
the direction that costs money, so it is worth returning to.

## 2026-08-22 — Contrarian selection amplifies the model's own errors

**Question.** If the five had competed across a whole season, publishing five
picks each gameweek, who would have won?

**Method.** Replay 2024-25 gameweek by gameweek. Each week every model refits on
what was knowable before the first kickoff, picks five in temperament, and the
week is graded against what actually happened. 22 gameweeks, 110 legs each.

**Result, the league table.**

| character | leg rate | slips won |
|---|---|---|
| bdog | 48.2% | 0 |
| alan | 38.2% | 0 |
| lily | 34.5% | 0 |
| valentina | 30.9% | 0 |
| tayler | 28.2% | 0 |

**Nobody won a single five-fold in 22 attempts**, which prompted the real
question: were the picks as likely as the models claimed?

**Result, the diagnosis. This is the finding.**

| | model said | actually happened | gap |
|---|---|---|---|
| **All legs on offer** (n=18,267) | 25.0% | 26.7% | **+1.7%** |
| Alan's picks | 47.6% | 38.2% | **-9.5%** |
| Bdog's picks | 51.6% | 48.2% | -3.4% |
| Valentina's picks | 34.0% | 30.9% | -3.1% |
| Tayler's picks | 27.9% | 28.2% | +0.3% |
| Lily's picks | 26.8% | 34.5% | +7.8% |

**Conclusion.** The model is well calibrated across everything it offers, very
slightly conservative. **The damage is done by the selection rule, not the
model.**

Alan and Bdog choose legs by how far they deviate from the pack. That reliably
selects the cases where their own model is most wrong, because the biggest
disagreement is usually the biggest error rather than the biggest insight. Alan
overstates his own picks by 9.5 points while being honest about the field.

Tayler explicitly avoids standing out, and is almost perfectly calibrated on
what he picks, at +0.3.

**This generalises well beyond these five.** Any selection rule that maximises
edge-versus-consensus is a machine for finding your own overconfidence. It is
the same reason a bettor who only backs prices they think are wrong needs to be
better calibrated than one who bets at random, not merely as good.

**A bug found alongside it, and worth separating from the finding.** The
competition's pick function enforced only the ceiling of the target band, not
the floor, so slips drifted far below 10%. Alan's five legs at a claimed 47.6%
combine to 2.4%, not the 10 to 20% the band was meant to guarantee. That
explains the zero slips independently of the calibration problem, and it is now
fixed. The calibration finding stands regardless, because it is measured
leg-by-leg rather than on the slips.

**Caveats.** 110 legs per character is a small sample and the gaps have wide
intervals. 22 gameweeks rather than 38, because the underlying data thins out.
Returns are settled at our own fair odds, which is self-referential: we set the
price we are paid.

## 2026-08-22 — We were overconfident exactly where it costs money

**Question.** Our published price floors sat above what bookmakers actually
offer, so the site said no bet on everything. Is the market right, or are we
overconfident?

**Method.** Calibration by line, from the walk-forward backtest, 13,993
predictions per market.

**Result.** Both, and the split matters.

| line | we say | happens | bias |
|---|---|---|---|
| 1+ fouls | 0.454 | 0.465 | +0.010 |
| 2+ fouls | 0.192 | 0.184 | -0.008 |
| 3+ fouls | 0.074 | 0.059 | **-0.015** |

The aggregate hides the problem. Broken out at the 3+ line, in the buckets that
would actually be bet:

| we say | happens | gap | n |
|---|---|---|---|
| 0.140 | 0.116 | -0.024 | 2,794 |
| 0.240 | 0.184 | **-0.056** | 837 |
| 0.340 | 0.298 | -0.042 | 255 |
| 0.444 | 0.312 | **-0.132** | 64 |

**Conclusion.** We are honest at the 1+ line and overconfident at 3+, which is
precisely where any value would live. This is the worst possible place to be
wrong, and the error runs in the direction that loses money: an overstated
probability produces fair odds that are too short, so a bet that looks like
value is not.

The likely mechanism is the negative binomial's tail. Dispersion is fitted
globally, so the same relative spread is applied to a player expected to commit
0.3 fouls and one expected to commit 2.5, and the tail is too fat for the
former.

Fitted a shrink-toward-base-rate correction per market and line by least
squares, and applied it before anything is published:

| market | 1+ | 2+ | 3+ |
|---|---|---|---|
| fouls committed | 0.904 | 0.905 | **0.776** |
| fouls drawn | 0.960 | 0.991 | 0.883 |

A factor of 1.0 would mean the raw number was already honest. Fouls drawn is
close to that. Fouls committed at 3+ sits at 0.776, so roughly a quarter of its
distance from the base rate was noise.

**Caveats.** This corrects the symptom, not the cause. The real fix is a
dispersion that varies with the expected count, which is a modelling change
rather than a post-hoc adjustment. The top bucket has only 64 observations, so
the correction there is fitted on very little and a richer per-bucket method
would be fitting noise with more noise. And the correction is fitted on the
same data it is evaluated on, which flatters it: it needs re-fitting on held-out
seasons before anyone trusts the number.

## 2026-08-22 — The five, finally compared on player markets

**Question.** The characters had never been backtested on player predictions.
They were built, eyeballed, patched twice and shipped. Do they actually differ,
and does any of it beat a naive model?

**Method.** Walk-forward by week from January 2024, refitting on rows knowable
before each week's earliest kickoff. 13,993 predictions per character per
market, scored at the 0.5, 1.5 and 2.5 lines. Predictions use each player's
ACTUAL minutes, so this measures the foul model alone rather than tangling it
with the minutes model.

**Result, fouls committed.**

| character | MAE | log loss | ECE |
|---|---|---|---|
| lily | 0.647 | **0.3972** | 0.0089 |
| bdog | 0.654 | 0.3974 | 0.0078 |
| valentina | 0.653 | 0.3975 | **0.0051** |
| alan | 0.662 | 0.4018 | 0.0130 |
| tayler | 0.647 | 0.4046 | 0.0249 |
| *position-prior baseline* | | *0.4133* | |

**Result, fouls drawn.**

| character | MAE | log loss | ECE |
|---|---|---|---|
| bdog | 0.631 | **0.3749** | 0.0076 |
| valentina | 0.631 | 0.3751 | 0.0069 |
| lily | 0.628 | 0.3765 | 0.0103 |
| alan | 0.643 | 0.3805 | 0.0125 |
| tayler | 0.633 | 0.3846 | 0.0270 |

**Conclusions, in order of how much they matter.**

**1. Player history genuinely adds signal.** Every character beats a model that
knows only the player's position and minutes, by around 4%. That is the result
that justifies the whole player-level exercise.

**2. The characters are barely distinguishable here.** Best to worst spans 1.9%
on committed and 2.6% on drawn. On match totals the spread was wider and the
ordering stable. Temperament matters much less once you are predicting one
player's count, because there is far less for a personality to disagree about:
a player's own rate dominates, and everything the characters vary is a second
order adjustment on top of it.

**This has a product consequence.** Presenting five characters as five sharply
different opinions overstates the case at player level. They are five slightly
different readings, and the site should not imply more.

**3. Different markets have different winners.** Lily takes committed, Bdog
takes drawn. With gaps this small, treating either as "the best" would be
reading noise.

**4. Tayler is worst on both, and worst calibrated.** His enormous shrinkage
helps on match totals, where noise dominates, and hurts here, where a player's
own record is the signal. Exactly in character, and a real cost.

**Caveats.** No confidence intervals on these yet, and with 1.9% separating
first from last that omission matters more than usual. The evaluation starts in
2024 to keep runtime sane, so it covers roughly a season and a half rather than
the full history.

## 2026-08-21 — Player data found. The blocker is gone

**Question.** Is there any free route to per-player, per-match fouls committed and drawn, given FBref is Cloudflare-blocked, FotMob objected to scraping and API-Football is suspended?

**Method.** Exhaustive source sweep, verifying by download rather than trusting dataset descriptions.

**Result.** Two sources, both plain file downloads with no scraping and no key.

| Source | Coverage | Rows | Fouls committed | Fouls drawn |
|---|---|---|---|---|
| `JaseZiv/worldfootballR_data` | Aug 2017 to Sep 2025 | 81,328 | `Fls`, 100% filled | `Fld`, 100% filled |
| `olbauday/FPL-Core-Insights` | 2024/25, 2025/26, live | ~24,000 | `fouls_committed` | `was_fouled` |

The first also carries minutes, position, tackles won, interceptions, cards and aerial duels: 2,857 matches, 1,671 players, 32 teams. The second updates three times daily via GitHub Actions, so it covers the current season as it happens.

Face validity is strong. Top fouls drawn per 90 across the sample: Grealish 3.89, Hazard 3.13, Bruno Guimarães 3.07, Zaha 3.04, Maddison 2.77. Those are the right names, which is the cheapest sanity check available and it passes.

**Conclusion.** Every player market is now buildable. This was the single biggest risk in the project and it is resolved without spending anything.

Also resolved: **FBref did NOT lose per-player fouls** in the January 2026 Opta termination. The columns moved from the Miscellaneous table into the match-report summary table. The obstacle there is Cloudflare, not missing data, which means FBref returns as a possible future source rather than being permanently dead.

**Caveats, and they are real.** Neither source declares a licence. `worldfootballR_data` was archived in September 2025 and is frozen. Both redistribute Opta-derived data. For private modelling this is fine; redistributing the raw data is not, and a future commercial phase needs this revisited properly. Recorded in [12-risks-and-open-questions.md](12-risks-and-open-questions.md).

The only permissively licensed option found, `khalidald/football-stack` under MIT, covers less. If licensing ever becomes the binding constraint, that is the fallback.

---

## 2026-08-21 — The five characters, and Valentina's first version failing

**Question.** Do five genuinely different models, each built around a temperament, actually diverge, and can any of them beat the champion?

**Method.** Five models sharing the same data and harness, differing in memory, shrinkage, confidence and features. Walk-forward from 2015-16, 4,180 predictions each.

**Result, first run.**

| model | MAE | log loss | ECE |
|---|---|---|---|
| bdog_bravery | 3.893 | 0.5690 | 0.0223 |
| champion | 3.916 | 0.5695 | 0.0062 |
| alan_anger | 3.912 | 0.5727 | 0.0199 |
| lily_lust | 4.077 | 0.5866 | 0.0548 |
| tayler_terror | 4.055 | 0.5906 | 0.0371 |
| league_mean | 4.133 | 0.5993 | 0.0141 |
| **valentina_violence v1** | **4.569** | **0.6505** | **0.1383** |

**Valentina v1 lost to the league average**, badly. She modelled cards alone and converted to fouls with a fitted ratio. Cards are a noisy proxy that has been drifting away from fouls for two decades, so the approach refutes itself.

**Conclusion.** The finding is real and worth keeping: **pure card-based foul modelling is worse than predicting the mean.** But shipping her that way breaks the rule that every character gets equal effort and none may be deliberately bad. Rebuilt as v2, where the aggression reading bends a foul-rate estimate rather than replacing it, which is what a competent analyst with her temperament would actually do.

**Result, v2.** Valentina moves from last to third, 0.5707, ahead of Alan.

**Bdog wins**, 5.33% better log loss than baseline and ahead of the champion. The contrarian construction genuinely adds something: fading the consensus of the other four is not just a gimmick.

**Tayler is second worst and perfectly in character.** Enormous shrinkage means he barely deviates from the average, which is exactly what terror produces. He will rarely be badly wrong and rarely be useful.

**Caveats.** Bdog beats the champion on log loss but the champion remains better calibrated at 0.0062 against 0.0091, so under the promotion rule the champion keeps the match-totals crown for now. Bdog costs four extra model fits per refit, since he must know what the others think.

---

## 2026-08-21 — Champion promoted, and the first published round

**Question.** Does scaling dispersion fix the calibration failure, and does the model then clear the promotion bar?

**Method.** Swept `dispersion_scale` over 0.55, 0.65, 0.75, 0.85 and 1.0 on `team_rates_referee`, walk-forward from 2010-11, 6,080 predictions.

**Result.**

| dispersion_scale | MAE | CRPS | log loss | ECE |
|---|---|---|---|---|
| 0.55 | 3.925 | 2.768 | 0.5749 | 0.0067 |
| **0.65** | 3.925 | 2.768 | 0.5749 | **0.0069** |
| 0.75 | 3.925 | 2.767 | 0.5754 | 0.0136 |
| 0.85 | 3.925 | 2.772 | 0.5764 | 0.0216 |
| 1.00 | 3.925 | 2.787 | 0.5783 | 0.0313 |
| league_mean baseline | 4.139 | 2.919 | 0.6028 | 0.0214 |

Calibration error fell 4.5x. The residual gaps are now within ±0.022, most within ±0.006. MAE is unchanged, as expected: dispersion changes the spread, not the central estimate.

**Conclusion.** Promoted `team_rates_referee` at `dispersion_scale=0.65` to champion for `match_total_fouls`. It now clears both promotion tests: 4.64% better log loss than the baseline, and better calibrated (0.0069 against 0.0214).

Chose 0.65 over 0.55 despite an identical log loss. The two are inside noise of each other, and 0.65 is the less extreme value, so it is the one less likely to be an artefact of this particular sweep.

Published the first round: 10 fixtures for 21 to 24 August 2026. Expected totals run from 20.29 (Man City v Bournemouth) to 22.56 (Brighton v Aston Villa).

**Caveats.** Dispersion is fitted globally, so every match gets the same relative spread. In truth a fixture with thin evidence should be predicted with a wider distribution than one with ten seasons behind it. The model does not yet do that, and it is the most obvious next improvement.

---

## 2026-08-21 — Confidence must be judged on effective sample size, not membership

**Question.** How should the site say "we do not really know" about a promoted club?

**Method.** The first cut flagged teams absent from the training data. It fired for nobody in this round, which was wrong.

**Result.** Coventry played in this league until 2001 and Hull as recently as 2016-17, so a membership test calls both known. Their time-decayed effective sample sizes are 0.0 and 0.1 matches. F Hallam has 3.9.

**Conclusion.** Membership is the wrong test. Flag on effective sample size, the same time-decayed weight the shrinkage uses, with a threshold of 10 effective matches. Below that a rate is mostly the league prior, and the site should say so.

This is the correct behaviour working as intended, not a bug: shrinkage already pulled those clubs to the prior. The failure was purely in how we described our own confidence, which for a project whose only asset is honesty about its own performance is worth getting right.

**Caveats.** The threshold of 10 is a judgement, not a fitted value. It only affects presentation, not any number.

---

## 2026-08-21 — Dispersion is too high, so the model hedges

**Question.** The champion beats the baseline on log loss but is worse calibrated than it. Why, and can it be fixed?

**Method.** Read the calibration table from the 20-season walk-forward (7,980 predictions, 4 lines each).

**Result.** A clean, monotonic S-shape:

| predicted | observed | gap |
|---|---|---|
| 0.163 | 0.115 | -0.048 |
| 0.249 | 0.205 | -0.045 |
| 0.349 | 0.311 | -0.037 |
| 0.549 | 0.556 | +0.007 |
| 0.744 | 0.777 | +0.033 |
| 0.839 | 0.877 | +0.039 |

Probabilities are compressed toward 0.5 in both directions.

**Conclusion.** The predicted distribution is too wide. Dispersion is estimated from the *marginal* variance of match totals, but part of that spread is exactly what the team rates now explain, so the residual variance is smaller than the marginal variance. The model is hedging.

Introduced `dispersion_scale` as a parameter and let the harness fit it rather than guessing. Estimating residual variance directly would be more principled but needs a prediction for every training row at every refit, which is far too slow at 380 refits.

**Caveats.** Scaling a variance is a blunt instrument. If the S-shape survives the sweep, the honest fix is isotonic calibration on held-out folds, which is already in the plan.

---

## 2026-08-21 — Lopsided games have FEWER fouls, and my hypothesis was backwards

**Question.** Does a mismatched fixture produce more fouls, because the underdog spends the game defending?

**Method.** Derived a mismatch score from closing 1X2 odds with the margin removed, `|P(home) - P(away)|`, across the 2,660 matches from 2019/20 that carry closing prices. Compared quartiles, then added it to the model as a multiplicative term with a fitted coefficient.

**Result.** The relationship is real, strong and **the opposite of what I predicted**:

| mismatch quartile | matches | fouls per match |
|---|---|---|
| Q1, most even | 665 | 22.69 |
| Q2 | 665 | 21.96 |
| Q3 | 665 | 21.60 |
| Q4, most lopsided | 665 | 19.92 |

Correlation -0.208. Monotonic across all four quartiles, and a 2.77 foul gap between the extremes, which is over 12%.

But adding it to the model made things **worse**: log loss 0.5974 against 0.5739 without it, and expected calibration error jumped from 0.0288 to 0.1003.

**Conclusion.** Two separate findings.

First, the football: a dominant side keeps the ball, and a team without the ball cannot foul. Territory and possession suppress fouls more than defensive desperation creates them. My original reasoning, written into the plan on 2026-08-21, was wrong.

Second, the modelling: the feature failed *because it is collinear with what the team rates already encode*. Strong teams are both dominant and low-fouling. Manchester City commit 8.25 fouls a match, the lowest in the league. Bolting a mismatch multiplier on top double-counts the same effect.

This is a concrete demonstration of the rule in [06-modelling.md](06-modelling.md): stacked multipliers double-count, and the fix is joint estimation. The mismatch signal belongs in a GLM alongside team effects, where the fit decides how much is left for it to explain, not multiplied on afterwards.

**Caveats.** Only 2,660 matches carry closing odds. The linear form may also be wrong: the quartile means suggest the effect accelerates at the lopsided end rather than running straight.

---

## 2026-08-21 — First walk-forward results

**Question.** Does anything beat a league average at predicting match total fouls?

**Method.** Walk-forward by weekly batch over 20 seasons, refitting before each batch on rows with `known_at <= as_of` and nothing else. 7,980 predictions. Metrics: MAE, CRPS, log loss across lines 20.5, 22.5, 24.5 and 26.5, and expected calibration error.

**Result.**

| model | n | MAE | CRPS | log loss | ECE |
|---|---|---|---|---|---|
| team_rates_referee | 7,980 | 4.048 | 2.865 | 0.5839 | 0.0285 |
| team_rates | 7,980 | 4.152 | 2.935 | 0.5960 | 0.0222 |
| league_mean | 7,980 | 4.286 | 3.021 | 0.6120 | 0.0223 |

Best is 4.60% better on log loss than the baseline. MAE 95% interval 3.982 to 4.117, which excludes the baseline's 4.286.

**Conclusion.** Team rates carry real signal, and a heavily shrunk referee factor adds a little on top. The improvement is modest, which is the expected shape for this problem: match totals are the most efficiently priced market we will touch.

**Not promoted yet.** The promotion rule requires beating the incumbent on log loss **and** being at least as well calibrated. `team_rates_referee` fails the second test, at 0.0285 against 0.0223. See the dispersion entry above.

**Caveats.** MAE around 4 fouls against a mean of 22 is a lot of irreducible noise, and most of it probably is irreducible. The referee factor is still a shrunk raw ratio and remains confounded by fixture assignment, so some of its apparent value may be team quality wearing a referee's name.

---

## 2026-08-21 — Fouls fell 19.6% while cards rose 16.3%

**Question.** Can 26 seasons be treated as equal evidence?

**Method.** Loaded every Premier League season from 2000/01 to 2025/26 from football-data.co.uk, 9,880 matches, and compared per-season means.

**Result.** Fouls per match fell from 26.92 to 21.64, a 19.6% decline. Cards per match rose from 3.31 to 3.85, up 16.3%, having peaked at 4.32 in 2023/24. Match-to-match standard deviation also fell, from 7.10 to 5.00.

**Conclusion.** No. A foul in 2026 is a rarer event and a more punished one than a foul in 2000. Exponential time decay is mandatory, with a half-life short enough to track it. Started at 400 days, to be tuned by the harness.

The narrowing spread matters too: an older season is not just biased, it is differently shaped, so pooling inflates the variance estimate.

**Caveats.** Whether the decline is refereeing interpretation, tactical change or data-collection change is unknown and probably unknowable from this data. It does not matter for prediction, but it would matter if we ever tried to forecast the trend itself rather than ride it.
