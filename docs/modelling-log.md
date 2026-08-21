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
