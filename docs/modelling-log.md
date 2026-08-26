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

## 2026-08-26 — Fixture congestion: a small old effect that no longer exists

**Question.** Oliver's angle: do tired teams foul differently? Days since the
previous match is free, computable from fixture lists already on disk, and
untested.

**Method.** 19,164 team-matches across 20 seasons of league data. Rest days
per team within a season, fouls demeaned per season (fouls fell 20% over the
window, so raw means would measure the era, not the rest).

**Result.** Over the full window, monotonic and small: 2-3 days' rest runs
0.15 fouls below the season mean, 8+ days runs 0.12 above, correlation 0.024.
In the modern era (2019 onward, 5,114 team-matches) it vanishes: correlation
0.0017 and the buckets are not even ordered.

**Conclusion.** Not a factor. Whatever squad rotation and sports science were
doing to tired legs in 2005, they have finished doing. A player-level version
(minutes accumulated in the last N days) is still untested, but the team-level
null lowers expectations, and it should wait behind ideas with measured
upside.

**Caveats.** League fixtures only: cup midweeks are invisible, so some
measured long rests were real short ones, which attenuates the effect toward
zero. That bias existed in both eras, and the old era still showed the
effect through it.

## 2026-08-24 — The refit calibration mostly says: stop correcting

**Question.** The published correction was fitted against the model before
today's two changes, both of which improved calibration, so it likely
over-shrinks now. Refit against the model as it is: season evidence attached,
match-store opponent factors on, same functional form, fit on walk-forward
predictions to July 2024 and evaluated on August 2024 onward, 22,523 pairs a
line (`backtest/calibration_fit.py`).

**Result**, held-out log loss and ECE, raw against old correction against new:

| market, line | old shrink | new shrink | held-out logloss raw / old / new | ECE raw / old / new | verdict |
|---|---|---|---|---|---|
| committed 0.5 | 0.9305 | 0.9282 | 0.5891 / 0.5885 / 0.5886 | 0.0246 / 0.0203 / 0.0205 | kept |
| committed 1.5 | 0.8820 | 0.9398 | 0.4002 / **0.4016** / 0.4003 | 0.0098 / **0.0148** / 0.0087 | kept |
| committed 2.5 | 0.7948 | 0.9039 | **0.1880** / 0.1912 / 0.1890 | **0.0055** / 0.0136 / 0.0093 | **published raw** |
| drawn 0.5 | 0.9770 | 0.9811 | 0.5713 / 0.5714 / 0.5714 | 0.0168 / 0.0101 / 0.0114 | kept |
| drawn 1.5 | 0.9922 | 1.0454 | 0.3719 / 0.3719 / **0.3733** | 0.0107 / 0.0101 / 0.0119 | **published raw** |
| drawn 2.5 | 1.0394 | 1.1000 | 0.1790 / 0.1792 / 0.1795 | 0.0057 / 0.0058 / 0.0055 | **published raw** |

**Three findings, in rising order of importance.**

**The old correction was actively harming the site.** At committed 1.5 it cost
0.0014 held-out log loss against raw and pushed ECE from 0.0098 to 0.0148, and
at committed 2.5, the line the correction was originally built for, it was the
worst of the three options on both metrics. It was fitted against a model that
no longer exists.

**The current model barely needs correcting.** Raw ECE on the held-out window
runs 0.0055 to 0.0246 across the six lines, with the only material
miscalibration at the 0.5 lines. This is the two shipped changes doing what
their gates said they did.

**Window drift is now bigger than the miscalibration left to correct.** The
new fits at drawn 1.5 and 2.5 came out ABOVE one, expansion, and then hurt on
held-out: what the 2022 to 2024 window teaches no longer holds in 2024 to
2025. The same lesson as the game-state slope moving 2.5x between periods.

**So the rule became part of the fitter: a correction earns its line or the
line is published raw.** Kept where it does not cost held-out log loss beyond
0.0002 and improves held-out ECE; absent otherwise, and the reader already
treats absence as pass-through. Three of six survive, all mild shrinks near
one. Stated plainly in `decide()`'s docstring and here: that keep-or-drop
consults the held-out window, six binary decisions, which is mild selection on
the test set, and the alternative was knowingly shipping two corrections
measured to hurt.

**Consequences.** Published 3+ committed probabilities RISE, since the 0.795
shrink at that line is gone, which also points the same way as the live
282-claim sample that suggested the old correction was aimed backwards. The
reference file now carries provenance, fitted-at, windows, n and a version.
The distributional redesign stays behind the pre-registered live sample, as
the plan of record placed it.

## 2026-08-24 — Pooling six leagues works exactly as designed and changes nothing

**Question.** The C3 gate. We hold 485,569 player-matches and read 81,327.
Does pooling the other five leagues, on one scale, improve predictions about
England? The gate is advisor 2's and it is strict: foreign data may not help
by sample size alone, it has to improve England out-of-sample scoring with the
offsets fitted only on what was knowable at each timestamp.

**Everything upstream of the answer checks out.** The fitted offsets are ESP
1.246, ITA 1.232, FRA 1.186, GER 1.132, USA 1.123, landing on top of the 23%
and 25% measured independently in `29-why-leagues-differ.md`. Across 1,020
players who changed league the rank correlation is **+0.689**, and applying
the offset shrinks the rate discontinuity at the border from -0.0467 to
-0.0295. Foul propensity travels with the player, which is what made this
worth trying.

**Result**, 7,246 English player-matches, August 2024 to February 2025:

| variant | log loss | ECE | thin n | thin log loss |
|---|---|---|---|---|
| england-only | 0.3905 | 0.0077 | 1,158 | 0.3666 |
| pooled-raw | 0.3911 | **0.0167** | 780 | 0.3524 |
| pooled-adjusted | **0.3902** | **0.0064** | 780 | 0.3528 |

Paired over the same 21,738 observations, pooled-adjusted against
england-only: **+0.00022 [-0.00043, +0.00085]** on committed and **+0.00020
[-0.00050, +0.00087]** on drawn. **Neither clears zero.** The gate fails.

**Two things are worth keeping out of that table.** Unadjusted pooling is
actively worse, and worst on calibration, ECE 0.0167 against 0.0077, so the
offset is doing real work even though the work buys nothing. And the mechanism
visibly operates: the thin bucket falls from 1,158 player-matches to 780,
meaning a third of thin players gain a real record from abroad.

**So the average was tested where it could not show anything, and then the
narrow case was tested too.** Most English player-matches belong to players
with a full English record, where pooling changes nothing by construction.
Restricted to arrivals from abroad, ten or fewer English matches and a real
record elsewhere: **312 player-matches, -0.00028 [-0.01033, +0.00930] on
committed and -0.00237 [-0.01498, +0.00954] on drawn.** Also null, point
estimates slightly negative, and with 312 rows the test has little power.
Stated plainly rather than read as a result in either direction.

**Not shipped.** The data stays on disk, the machinery stays tested, and the
rank-transfer number stands on its own as something worth knowing.

**The most likely reason it is null, and it is testable.** A single
multiplicative intercept moves the position priors: fitted on 2024-10-01, the
DM prior is 1.423 england-only against 1.345 pooled-adjusted, and FW 1.276
against 1.238, about 5% in both cases even though the league rate matches
England exactly at 0.970. The intercept is right for the league as a whole and
slightly wrong per position, which is precisely the league-by-position
interaction `29-why-leagues-differ.md` said to test rather than assume.
Registered in `ideas.md`.

## 2026-08-24 — Take-ons are the drawn market's real correlate, and worth about one point

**Question.** Fouls drawn is the market we model worst, and every feature it
has describes defending. The data survey named `final_third_entries` and
`pen_area_entries` as the two most plausible additions, so both were fetched
across 34 seasons. Do they help?

**They are not the ones that matter.** Across 6,549 player-seasons with 900+
minutes:

| feature per 90 | corr with drawn | corr with committed |
|---|---|---|
| **take-ons attempted** (`total_contest`) | **+0.523** | +0.116 |
| penalty-area entries | +0.235 | -0.001 |
| touches in opposition box | +0.225 | -0.001 |
| final-third entries | **-0.182** | -0.060 |
| touches | +0.032 | -0.025 |

**The strongest signal was already on disk and the two just fetched are the
weak ones**, one of them pointing the wrong way. Worth recording plainly: the
survey's reasoning was that entering dangerous areas draws fouls, and the data
says what draws fouls is running at a defender with the ball, which is a
different thing.

Take-ons are also specific in the right direction: +0.523 on drawn against
+0.116 on committed, which is what the mechanism predicts and a good sign the
correlation is not just "busy players do more of everything".

**And it survives position.** Within every position group the relationship
holds, from +0.205 for forwards to +0.428 for right wingers, so take-on volume
is a genuinely separate axis from what position already tells us.

**Which made the out-of-sample result disappointing.** Fitting priors on
seasons to 2021/22 and scoring on 2022/23 onward, 1,159 held-out
player-seasons:

| prior | variance explained |
|---|---|
| grand mean | 0% |
| position mean, what ships today | 28% |
| take-ons alone | 26% |
| position and take-ons together | **29%** |

**One point.** The within-position correlations promised more than the
combination delivers, because the take-on slope is itself noisy out of sample.
And a prior only binds for thin players, so one point of variance on the
minority of predictions that use it will not survive contact with the full
pipeline.

**Not shipped.** The mechanism is real and the number is too small, which is a
different verdict from the three "real signal, worse model" results already in
this log and deserves its own wording: real signal, marginal model. The
fetched columns stay, since they cost a minute and the negative result is
worth keeping visible. Take-ons as a thin-player feature rather than a prior
is registered in `ideas.md` as the version that has not been tested.

## 2026-08-24 — Players in a match do not move together, measured directly this time

**Question.** The shared match effect has been argued about for three rounds
with two external advisors. The variance decomposition said there was nothing
missing; advisor 2 accepted that but named the hole in it, and we accepted the
naming: a fitted shared sd of zero rests on the model's own conditional
variances being right, so overstated idiosyncratic variance could cancel
against missing positive covariance and hide a real factor. This is the test
that does not route through the decomposition at all.

**Method.** `backtest/pairwise_dependence_study.py`. Standardise every
residual by its own predictive spread, average the pairwise products within
each match, teammates and opponents separately. Under independence both are
zero. Intervals bootstrap whole matches, never rows, because rows within a
match are the dependence being measured. Planted shared factors of 0.25 and
0.35 are recovered by the tests, so a zero here means zero rather than a blunt
instrument.

**Result**, 2024 onward, 99,201 teammate pairs and 105,783 opponent pairs:

| market | teammates | opponents |
|---|---|---|
| committed | **-0.0024** [-0.0089, +0.0043] | **+0.0110** [+0.0034, +0.0199] |
| drawn | +0.0029 [-0.0030, +0.0092] | +0.0049 [-0.0029, +0.0112] |

**Teammate correlation is zero in both markets.** Three of the four intervals
span zero. The fourth, opponents on committed, does not: there is a real but
tiny cross-team correlation of about +0.011.

**That is not the signature of a shared match factor, and the distinction
decides it.** A per-match intensity moves all twenty-two players together, so
it lifts teammates and opponents alike, which is asserted in the tests against
planted factors. Here teammates sit at zero while only the cross-team pairing
lifts, and only on fouls committed. Whatever that is, and reciprocal fouling
between two sides is the obvious candidate, it is not the missing shared
variance the audits proposed.

**And the practical size is the part that settles it.** Two-leg doubles at the
0.5 line, priced by multiplying marginals: predicted 0.2154 against 0.2160
observed on committed, which is 0.28% relative, and predicted 0.2012 against
0.1972 on drawn, which is 2% in the OTHER direction. Combination tickets priced
under independence are right, and the caveat printed under them can now quote a
number instead of hedging.

**Consequence.** The reopen condition recorded in `ideas.md` is not met, so the
Poisson-lognormal shared-intensity model stays retired, now on direct evidence
rather than on a decomposition with a caveat attached. The masking worry in
`25-match-variance.md` is closed. Match-level DISCRIMINATION remains open and
untouched by this: none of it says the match environment is unpredictable, only
that players within a match do not move together once the model has spoken.

## 2026-08-24 — Live opponent factors: neutral on equal footing, better when the archive is frozen

**Question.** The C2 stage one gate. Opponent and referee factors are computed
from the player archive, which stopped in September 2025, while the match
store is current through May 2026. Is the swap worth making?

**The first answer was no, and it was the wrong question.** Over 2024 onward,
where both sources are contemporaneous, the swap is a wash: 13,993
player-matches, log loss 0.3963 to 0.3960 on committed and 0.3744 to 0.3741 on
drawn. Fourth-decimal moves. Adding the referee factor on top changed nothing
again, 0.3959 and 0.3739.

**That window cannot see the thing the swap is for.** Production runs a frozen
rate source against fixtures a year past the freeze. So the study gained
`run_frozen`, which reproduces exactly that: the player archive cut at
14 September 2024, the match store left whole, predictions over October 2024 to
February 2025.

| market | variant | log loss | ECE | MAE |
|---|---|---|---|---|
| committed | frozen archive | 0.3918 | 0.0137 | 0.649 |
| committed | **frozen rate, live context** | **0.3913** | **0.0105** | **0.645** |
| drawn | frozen archive | 0.3813 | 0.0108 | 0.636 |
| drawn | **frozen rate, live context** | **0.3807** | **0.0074** | **0.633** |

**Both markets improve, and the calibration gain is the real one**: ECE falls
23% on committed and 31% on drawn. Log loss moves 0.0005, about 11% of the
0.0046 that staleness costs in total, which sits sensibly beside C1's 78% of
the same gap. They fix different inputs and they add up.

So the currency argument stopped being an argument. It is a measurement, which
is what the release gate demanded.

**Shipped: the opponent factor only.** `publish/player_round.py` attaches a
`MatchContextSource` to all ten models. Live divergence is material where you
would expect: Tottenham 1.154 on the archive against 1.050 on the store,
Man United 0.902 against 0.947, Sunderland 1.000 against 1.046, all driven by a
2025/26 season the archive does not contain. Promoted clubs still fall to their
Championship prior below five effective matches, tested both ways, because a
club with no top-flight rows reading 1.0 is the failure this project exists not
to make.

**Not shipped: the referee factor.** Published player predictions carry no
referee factor at all today, so wiring one is an addition rather than a swap,
and the equal-footing test measured it adding nothing. Three things have now
shipped here that were real signal and a worse model. This one stays out until
something measures it in.

## 2026-08-24 — Season totals recover most of the stale year, so they ship

**Question.** The C1 gate from `34-final-plan.md`: how much of what staleness
costs do season totals actually recover? Answered by replaying the live
situation one year earlier, where per-match truth exists: archive cut at
14 September 2024, predictions over October 2024 to 3 February 2025, four
evidence variants on identical player-matches
(`backtest/season_total_study.py`).

**Result**, house model, 5,408 player-matches per variant:

| variant | committed log loss | ECE | drawn log loss | recovered |
|---|---|---|---|---|
| stale (today's live situation) | 0.3918 | 0.0137 | 0.3813 | 0% |
| deep-history (completed seasons only) | 0.3915 | 0.0119 | 0.3811 | 3 to 6% |
| **running-totals** | **0.3882** | **0.0092** | **0.3759** | **78 to 87%** |
| oracle (never froze) | 0.3872 | 0.0104 | 0.3751 | 100% |

**The blend recovers 78% of the stale-to-oracle gap on committed and 87% on
drawn, and calibration IMPROVES** (ECE 0.0137 to 0.0092 on committed), so the
gate's second condition, no calibration damage, is met with room. Deep
history alone is worth little, 3 to 6%, exactly as the decay maths predicts:
what matters is the running reading of the season in progress, which is what
production holds through the complete 2025/26 totals plus refreshed 2026/27
fetches. The running totals in the study are reconstructed from withheld
archive rows, which is stated in the study docstring: the league genuinely
published those numbers at the time, we replay what a settle job would have
held.

**Shipped.** `publish/player_round.py` now refreshes the in-progress season
file, builds the evidence, attaches it to all ten models and extends the
squad-resolution universe with evidence-only names, so a 2025/26 arrival
resolves to the name his evidence is filed under. Every prediction's `why`
carries `seasonEvidenceNineties` and `priorFrom` gains a `season-totals`
state, because a totals-only player must not read as a watched record. The
evidence feeds ONLY the rate: minutes, opponent factors and the published
plain rate still read real matches. `season_evidence_weight` stays 1.0, the
value the gate run used; anyone refitting it does so through the study.

**The size of it in the current round, measured after the fact.** Of 609
players in the twenty squads, 396 resolved to a record before this and **505
do now**: 109 players who were being priced at their position's average have
a real one. Adding the evidence names to the resolution universe cost nothing
at the join, checked rather than assumed: zero previously-resolving players
became ambiguous, which was the obvious way this could have gone wrong.

**Not done here.** The character parameter sets were not re-run through the
gate individually; the house result carried the decision. If a character's
live behaviour looks wrong after this lands, that is the first place to look.

## 2026-08-24 — The provider offset is not real, and the archive has a hole nobody knew about

**Question.** Both external reviews demanded the FORM of the +4.6% provider
offset be measured before the C1 blend applies it: a multiplicative gap and an
additive one distort different players differently. So: how big is the gap per
player, in what form, and is it stable across seasons, positions and volume?

**Method.** `backtest/provider_offset_study.py`. League API season totals
joined to archive player-seasons through the identity rules (`resolve_names`,
token-subset both directions, ambiguity refused), never by raw name. 3,133
pairs across seven complete archive seasons. Pairs whose minutes disagree by
more than 5% are excluded from the form fit and counted.

**Result 1: there is no provider offset at player level.** The matched-pair
ratio is **1.0002 globally** and 0.9997 to 0.9998 in every season where the
archive is complete, flat across volume quintiles (0.999 to 1.001) and
positions. The two providers count the same player's fouls identically.

**The +4.6% was a composition artifact.** The league's fouls table only
carries players with at least 1 foul. In 2023/24 the archive has 76 zero-foul
players holding 37,227 minutes; drop them and the archive aggregate rate is
1.0601 against the API's 1.0558. The published league-level offset compared
each provider's own player set, and the sets differ by exactly the zero-foul
tail. Consequence: **the C1 blend needs no counting correction**, and any
league-AGGREGATE rate computed from the API fouls table overstates by about
5% unless the zero-foul minutes are restored.

**Result 2: the archive has a third hole.** The minutes-disagreement filter
lit up on 2021/22: 347 of 432 pairs disagreed, API always higher, Ramsdale
3,060 minutes against the archive's 2,340. The API is right. **The archive is
missing 75 of 380 matches of 2021/22, nearly all of April and May 2022**, and
7 matches of 2022/23. The gap table in `28-foul-data-sources.md` listed
neither. Season totals therefore patch three holes, not one.

**Result 3: the fetch was truncating at the page cap.** Exactly 500 rows of
minutes in season after season is not a coincidence, it is `pageSize=500`
with no pagination. `fetch_stat` now reads every page, and
`repair_truncated` refetched every stat whose count sat exactly on the cap:
**141 stats across 23 season files**. After repair, "in the minutes table but
absent from the fouls table" is testable as "zero fouls": 67 of the 69
determinable archive zero-foul players read exactly that way, with 2
anomalies (API shows 1 to 2 fouls where the archive shows 0) left excluded
and flagged rather than explained away.

**Consequences.** `data/reference/provider_offset.json` carries the measured
ratios with provenance and the blend reads it rather than a constant. The C1
eligibility rule gains a zero-foul branch: minutes present, fouls absent,
season repaired, reads as zero with a flag. The 2 anomalous pairs stay out.

## 2026-08-23 — Our predicted eleven is 63% right, and that is the real problem

**Question.** Every player bet depends on the player playing. Before confirmed
lineups land, roughly an hour before kickoff, we guess the eleven by ranking a
club's available players on starts then minutes. How good is that guess?

**Result**, 1,122 team-matches from August 2023:

| | |
|---|---|
| Slots correct | **62.9%** (7,760 of 12,342) |
| Average correct per XI | **6.9 of 11** |
| All eleven right | **0.6%** |
| Five or fewer right | **18.3%** |

Sportmonks sells human-curated expected lineups at about **84%** for the Premier
League, for 34 euros a month. That is a twenty-point gap on the one input every
player bet depends on.

**The model's own P(start) is worse, not better.** The two-stage minutes model
computes a time-decayed probability of starting and nothing used it to pick an
eleven, which looked like a free win. Measured over 739 team-matches it scores
**61.2%** against the counter's 65.1%. The half-life is the reason: at 1,000
days it is slow to notice a player becoming a regular, where a count of this
season's starts notices immediately. Not shipped.

**What this actually means for the product.** The confirmed-lineup poll already
runs and is 100% accurate, so the answer is not a better guess but a clearer
separation. A pick published before lineups is a different product from one
published after, they are already graded separately, and the site should make
that distinction much louder than it currently does.

For the window before confirmation there are three options and none is free and
good: keep the 63% guess and label it, pay for an 84% feed, or publish nothing
until lineups land. That is a product decision rather than a modelling one.

## 2026-08-23 — The first graded calibration points the wrong way

**Built the reliability view**, which answers the only question that matters
about a probability: did the things we called 60% happen 60% of the time. A hit
rate cannot, because a model that calls everything 50% and lands half of them
looks identical to one that knows what it is talking about.

**And the first reading is uncomfortable.** Over 282 graded claims from the
house model, almost every band comes in ABOVE what was said:

| band | we said | it happened | claims |
|---|---|---|---|
| 0 to 10% | 6 | **14** | 84 |
| 10 to 20% | 15 | 13 | 64 |
| 20 to 30% | 25 | **35** | 37 |
| 30 to 40% | 36 | **50** | 30 |
| 40 to 50% | 46 | 46 | 26 |
| 50 to 60% | 55 | **67** | 24 |
| 60 to 70% | 64 | 57 | 14 |

Published probabilities carry a correction fitted for measured OVERconfidence.
Live, the model is UNDERconfident, which means the correction may now be
pushing the wrong way.

**Nothing has been changed.** This is 282 claims across two matchdays, and the
whole discipline here is that no model changes on one week's results, ever.
Reversing a correction on a sample this size would be exactly the fiddling the
weekly review exists to prevent. If the direction holds over a few more rounds
the calibration correction is the first thing to re-examine, and this entry
exists so that gets checked rather than remembered.

The site states this on the page rather than leaving the chart to be read
unaided, including that it is too early to act on.

## 2026-08-23 — Position pairings predict nothing the team rate did not already say

**Question.** Two midfielders who both foul a lot ought to make for a busier
afternoon than the same two clubs with mild ones. Does facing a specific
exceptional foul-winner move a player's fouls beyond what his opponent's CLUB
average already implies?

**Method.** 9,419 player-matches from 2024 with a known opposing eleven. For
each, the opponent's best foul-drawing player as of that date, from training
data only, against the residual left by a model that already applies a
team-level opponent factor.

**Result.** Nothing.

| opponent's best foul-winner | n | predicted | actual | residual |
|---|---|---|---|---|
| under 1.67 per 90 | 1,893 | 0.903 | 0.831 | -0.072 |
| 1.67 to 1.91 | 1,879 | 0.909 | 0.863 | -0.045 |
| 1.91 to 2.20 | 1,884 | 0.972 | 0.868 | -0.104 |
| 2.20 to 2.58 | 1,879 | 0.963 | 0.887 | -0.076 |
| over 2.58 | 1,884 | 1.060 | 0.981 | -0.079 |

Correlation with the residual is **-0.003**, which is zero.

**The interesting column is `predicted`, not `residual`.** It climbs from 0.903
to 1.060 across the buckets, and `actual` climbs with it. The effect is real and
the model already has all of it, through the opponent factor. A side with good
foul-winners draws more fouls, that shows up in the club's rate, and knowing
WHICH of their players is the good one adds nothing on top.

**Consequence for the site.** The "opposite" names under each defender on the
stats sheet stay, because knowing who a player will be dealing with is
legitimately interesting to read. They are now labelled as context and the page
says outright that they predict nothing. Calling that column a signal would be
the exact failure this project keeps testing for.

## 2026-08-23 — Valentina gets a method, and it changes almost nothing

**The gap.** The five characters were meant to be five ways of reading a match.
They were five settings of the same calculation: memory length, shrinkage,
opponent weight, dispersion. Valentina, described as the one who reads the
matchup, read it by having `opponent_weight` set to 1.6. Turning a dial up is
not a different way of thinking.

**Does the thing she is supposed to read exist?** Across 9,120 matches, each
fixture's fouls were compared against what the two clubs' own season rates
imply. Splitting each pairing's history in half and correlating the halves, over
428 pairings with eight or more meetings, gives **+0.138**. The spread of pairing
means is 2.17 fouls where noise alone would produce 1.90, so the real pairing
effect is about **1.06 fouls on a base near 21**, roughly 5%.

Real, then, and small, and mostly noise: a split-half of 0.138 is a reliability
near 0.24, so about three quarters of any observed pairing residual is nothing.
Using it raw would repeat the promoted-clubs mistake exactly, where a
Championship rate at face value scored 16% worse than a plain league average and
only helped once shrunk to 37% of itself.

**Result**, 26,329 walk-forward player-matches:

| variant | log loss | ECE |
|---|---|---|
| Valentina without head-to-head | 0.4001 | 0.0069 |
| Valentina with head-to-head | **0.4000** | 0.0069 |

**Shipped anyway, and the reason is not accuracy.** One ten-thousandth of a log
loss is nothing. It ships because it makes her genuinely different in KIND
rather than in degree, which is what the five were supposed to be and were not.
After the adjustment she is the only one who notices that the Merseyside derby
runs about 2% above what Everton and Liverpool are worth separately.

Worth recording that this is the first change in several not to make the model
worse. Count-specific dispersion, the cards blend, the involvement widening and
game state all did. That it merely does no harm is, at this point, the
encouraging version.

**The remaining honesty problem is unchanged.** The five still separate by about
2% on player markets. One of them now has a method the others do not, which is
a start, and the site should keep saying how small the differences are rather
than letting five portraits imply five sharply different opinions.

## 2026-08-22 — Game state from closing odds: real signal, worse model

**Question.** Fouls should depend on who has the ball. Possession would say it
directly and we do not hold it: it is not in the 26 seasons of match files and
the feed that carried it was deleted in January 2026. Closing match odds ARE in
those files, back to 2000, and they measure the same thing more directly, since
possession is itself a proxy for expected game state.

The match-level version was already tested and failed. This is the asymmetric
version, which is different: a heavy underdog defends deeper and chases, the
favourite has the ball, so the same mismatch pushes the two sides in OPPOSITE
directions and a match total, which sums them, cancels it out.

**The effect is real and it is not the one I predicted.** Over 23,893 scored
player-matches, residuals against the model run cleanly with the market's view
of the fixture:

| team's win probability | residual |
|---|---|
| under 20% | -0.024 |
| 20 to 35% | -0.034 |
| 35 to 50% | -0.035 |
| 50 to 65% | -0.074 |
| 65 to 80% | -0.081 |
| over 80% | **-0.164** |

Monotonic across six buckets. But the story is **favourites foul less than
their own rate predicts**, by about 0.14 on a base near 0.9, roughly 15%. The
underdog end is nearly flat. I had expected the opposite.

**Three attempts to use it, all worse than not using it:**

| attempt | log loss | ECE | bias |
|---|---|---|---|
| current model | **0.4285** | **0.0139** | +0.0505 |
| slope fitted on 2022-24, centred at 0.5 | 0.4297 | 0.0213 | +0.0779 |
| slope fitted on all history, centred at 0.5 | 0.4292 | 0.0195 | +0.0713 |
| slope fitted on all history, mean-centred | 0.4289 | 0.0167 | +0.0616 |

Each fix addressed a real fault and each left it still losing.

**Two faults were mine, and worth keeping visible.** Centring the correction at
a win probability of 0.5 scales UP every underdog and DOWN every favourite, and
there are far more of the former, so it raised the average prediction of a model
that already over-predicts. And fitting the slope on 2022-24 picked the strongest
window there has been: successive two-year slopes run -0.105, -0.150, **-0.261**,
-0.130, so that fit over-corrected by a factor of two.

**I guessed wrong about why, and checked.** The first explanation was
collinearity with the opponent factor, which is what killed the match-level
version. Measured, the correlation between win probability and opponent factor
is **-0.044**. Not collinear. The explanation was plausible and false, and it
would have gone into this log unchallenged if I had not measured it.

**What is left.** The effect is real, consistent in direction across eight
years, and too small and too unstable to beat the noise a correction adds. A
6 to 9% adjustment sits far below per-observation variance while the slope
itself moves by a factor of 2.5 between periods. Not shipped.

The study is kept at `backtest/game_state_study.py` and the stability check at
`backtest/game_state_stability.py`, so the next person tempted by this can see
it was tried rather than assume it was missed.

## 2026-08-22 — The loop closes, and two bugs that would have faked it

**What was missing.** The grading job has existed since the start. Nothing ever
built the outcomes it needs, so nothing had ever actually been graded. The
weekly review was a document describing a job that did not run.

**Why settlement works by subtraction.** The league's API publishes per-fixture
stats at TEAM level and per-player stats only as SEASON TOTALS. A player's fouls
in one match are the difference between two weekly snapshots and are not
available any other way: the worldfootballR archive stops in September 2025 and
FBref lost its Opta feed in January 2026. A bulk ranked endpoint makes it cheap,
two calls rather than one per player.

The subtraction is only valid when a player made exactly ONE appearance between
snapshots. In a midweek round he may have made two, and then the difference is a
sum whose parts are unknowable. Those are skipped and counted.

**Two bugs, caught because the first result was impossible.** The first run
reported 24 claims graded, 0 of them winning, against a claimed 26.6%. That is
roughly a 1 in 1,400 event, so it was not variance.

1. **The join was on the wrong name.** Predictions recorded "Havertz" and the
   outcomes carry "Kai Havertz". Only 24 of 1,913 claims joined, and those were
   the players whose display name happens to equal their full name. Predictions
   now record the full name.

2. **Nothing checked the fixture had finished.** Outcomes are keyed by player and
   market with no fixture in the key, so a Saturday appearance would settle a
   claim about a Tuesday match. This would never have failed loudly. It would
   have quietly produced a track record that looked real. Settlement now grades
   only fixtures the league reports as complete.

The first is the name-keyed join failure again, in a second place, on the same
day it was found in `opponent_factor`. Twice in one session is a pattern worth
naming rather than fixing twice.

**First honest numbers**, 293 claims over two completed fixtures:

| model | n | claimed | actual | gap |
|---|---|---|---|---|
| house | 264 | 29.5% | 28.0% | -1.5% |
| tayler | 11 | 76.1% | 100.0% | +23.9% |
| bdog | 11 | 64.8% | 54.5% | -10.2% |
| alan | 7 | 65.2% | 0.0% | -65.2% |

The house model is well calibrated at -1.5% over 264 claims. **Every character
number here is noise.** Seven to eleven claims says nothing at all, and Alan's
0% no more than Tayler's 100%. They are shown because hiding the early sample
would be the start of exactly the selective reporting this is meant to avoid.

## 2026-08-22 — Half the league had no opponent adjustment at all

**Found while doing something else**, which is the usual way. Building priors
for promoted clubs meant reading `opponent_factor`, and it returns 1.0 whenever
it finds fewer than 200 rows for an opponent.

Fixtures spell a club "Man United". The player history spells it "Manchester
United". The lookup found nothing, fell through the thin-evidence branch and
returned 1.0, which reads as "this opponent is perfectly average" rather than
"I could not find this opponent".

**It was not a small effect.** Roughly half the clubs were affected, and the
discarded adjustments were large:

| club | factor being used | factor available |
|---|---|---|
| Manchester United | 1.000 | 0.844 |
| Tottenham | 1.000 | 1.247 |
| Newcastle | 1.000 | 1.261 |
| Brighton | 1.000 | 1.119 |

This is exactly the failure the no-name-keyed-joins rule exists to prevent, and
it reached published output anyway. The name is now resolved through the
crosswalk before the lookup, and both spellings are asserted equal in a test.

**The deeper fault is the silent default.** Returning 1.0 for "not found" and
for "genuinely average" makes the two indistinguishable, so nothing could ever
have alerted us. Thin evidence now routes somewhere that can say it has nothing.

---

## 2026-08-22 — Promoted clubs, and the version of the fix that loses

**Question.** Coventry, Hull and Ipswich came up for 2026/27 with no Premier
League history, so they took the league average. Can second-tier data do better?

**What is not available.** ⚠️ Corrected 2026-08-26: this said Championship
PLAYER data does not exist at any price. It does. The Premier League's own API
carries ranked player stats for competition 12, free and unauthenticated. They
are season totals rather than per-match rows, so they publish a rate and do not
train a model. See `sources/player_stats.py` and docs/40. The rest of this
entry stands.

Championship PLAYER data was believed not to exist at any price.
FBref's advanced stats cover the top five European leagues only, so there is no
second-tier fouls-per-player table to download. Individual rates for a promoted
club's squad stay unknown, and this fixes the TEAM prior only.

**The obvious version makes it worse.** Every promotion since 2001 gives a final
Championship season and a first Premier League season, 66 pairs. The mean ratio
between them is **0.990**, which says fouls transfer untouched and invites using
the Championship rate directly. Doing that scores **16% worse** than the plain
league average.

The ratio is a trap. Championship foul rates are spread far wider than Premier
League ones, so a club 3 fouls above its division average does not arrive 3
fouls above the Premier League average. Regressing deviation on deviation gives
a slope of **0.373**: only about 37% of a club's distinctiveness survives
promotion, despite the two correlating at +0.63.

**Result**, leave-one-out so the slope never sees the club it predicts:

| predictor | fouls committed | fouls drawn |
|---|---|---|
| league mean, what we did | 0.907 | 1.173 |
| Championship rate, raw | 1.051 (**-15.8%**) | 1.164 (+0.7%) |
| **Championship deviation, shrunk** | **0.838 (+7.7%)** | **1.081 (+7.8%)** |

Both directions improve by about 8%. Both raw versions do not.

**Worth keeping in view.** A correlation of +0.63 looked like permission to use
the number. It was permission to use 37% of it. The same trap is waiting in any
feature imported from a different population, and the check is cheap: score it
against the baseline it claims to beat.

## 2026-08-22 — Averaging minutes hid a bimodal truth

**Question.** Expected minutes was a time-decayed average of a player's last ten
matches. A rotation player alternating 90 minutes and 0 came out at 45. He has
never once played 45 minutes. Does describing that honestly help?

**Why it never showed up.** The mean is unaffected. E[fouls] = rate x E[minutes]
either way, so every bias check we ran came back clean. Only the SHAPE is wrong,
and the shape is what a bet settles on.

**Method.** Split minutes into whether he plays and how long: P(start), P(bench),
P(unused), with separate minutes for starting and substitute appearances. The
prediction becomes a mixture over those branches, with the unused branch a point
mass at zero rather than a small number.

Testing it needed a new harness. The existing one scores with the minutes a
player ACTUALLY played, deliberately, so it measures the foul model alone and is
blind to this. The source data holds only appearances, so non-appearances were
reconstructed: anyone who played for a team in the previous 30 days but not in
this match counts as 0 minutes and 0 fouls. That over-counts, sweeping in the
injured, suspended and sold, but it is the population we publish on.

**Result**, 55,167 scored predictions from 2024:

| variant | log loss | ECE | says P(0 fouls) |
|---|---|---|---|
| average minutes | 0.3868 | 0.0522 | 0.531 |
| **two-stage mixture** | **0.3831** | **0.0491** | 0.560 |
| *actually zero* | | | *0.646* |

**Conclusion.** A 1.0% log loss improvement, twice what the cards model managed
against its baseline, and calibration improves alongside it. Kept.

The remaining gap on zeros is partly an artefact: the reconstruction counts an
injured player as an available one who did not play, which inflates the observed
0.646. How much is artefact and how much is real is not yet separated, and it
needs actual squad lists rather than a 30-day proxy to settle.

**The useful part is the interface, not the number.** `minutes_profile` takes a
`confirmed` argument, so when an official lineup lands an hour before kickoff,
P(start) collapses to 1 or 0 and the mixture rebuilds itself. Averaging had
nowhere to put that information.

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
