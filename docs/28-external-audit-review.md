# Review of the two external methodology audits

**Status: Written 2026-08-23, against the code and docs as of that date.
Addendum 2026-08-23: both advisors replied (see `audit-responses/`). Advisor 1
accepted every disposition. Advisor 2 accepted the direction and pressed three
challenges that this document's phrasing partly earned: "retired by
measurement" overstates what the variance decomposition shows, calibration is
red/amber rather than apparatus-pending, and several "already built" claims
are assertions until their evaluation tables are visible. The accepted
corrections and the committed plan live in `29-next-phase-plan.md`, which
supersedes the phase 1 sketch below. Read the shared-variance rejection in
this document with the agreed phrasing: the specific shared-random-effect
explanation is unsupported by the decomposition, and match-level
discrimination remains an explicit open research question.**

Two external advisors reviewed the methodology. Advisor 1 wrote a short
architectural audit ("Technical Audit & Architectural Blueprint"). Advisor 2
wrote a long statistical audit ("Statistical, Modelling & Engineering Audit",
112 sections), working from `27-how-it-works.md` alone.

This document reviews both against what is actually built, states what we will
take into a phase 1 run, what goes to the ideas register, and what we reject
with reasons. Every pushback below was itself stress-tested before being kept;
where the pushback survived only in part, that is said.

One meta-point first: both audits reasoned honestly from a stale number. The
39% match-level under-dispersion they treat as the biggest open problem was
re-measured on 2026-08-23 and superseded (`25-match-variance.md`), but
`27-how-it-works.md` still lists it as open. That is our doc rot, not their
error, and fixing 27 is part of this review's actions.

---

## 🎯 Verdict in one paragraph

Advisor 2's audit is the more useful of the two: roughly a third of it
recommends things already built (which validates the engineering), a third is
genuinely new and good (the substitute programme above all), and a third is
blocked on data or superseded by measurement. Advisor 1's audit is right about
the product-level tension in publishing amplified character probabilities and
wrong in most of its remedies: it proposes deleting the thing that makes the
product a product, a variance fix the data says is not needed, and an odds
pipeline that is either not available or not permissible. The single biggest
prize in either document is making substitutes a first-class model, and it is
feasible with data we already hold.

---

## ✅ What the audits recommend that is already built

Worth listing because advisor 2 saw only the methodology page, and because
"already done" is the strongest possible response to a recommendation.

| Recommendation | Where it already lives |
|---|---|
| Separate fouls committed and fouls drawn (A2 §2, P0 item 1) | Two markets: `PlayerFoulModel` and `PlayerFouledModel`, both backtested and calibration-corrected. Involvement is their convolution, and independence was measured to beat the correlation-corrected version over 59,649 player-matches (`involvement.py`) |
| Directional opponent effects (A2 §3) | The opponent factor is computed per market from the market's own stat, so committed and drawn ask mirrored questions by construction. The promoted-club fallback applies to committed only, for exactly the directional reason the audit gives |
| Margin and overround handling (A2 §26) | `markets/odds.py`: 15% prop margin stated, compounding take-out per leg, fair odds only (ADR-009) |
| Temporal honesty as an engineering invariant (A2 §73 to 75) | `known_at` on every fact, walk-forward harness, instrumented read-tracking, canary test in CI (`07-backtesting.md`) |
| Missing must never read as average (A2 §76, 109) | Repo rule 2, ADR-007 identity halts the pipeline, and the opponent-name bug that motivated the rule is documented with a guard test |
| Prediction provenance and immutable versions (A2 §78 to 79) | Append-only JSONL keyed by model id and version, never edited, manifests with git sha, config hash and snapshot id |
| Canonical house model (A2 §30) | The house parameter set is the default and the champion protocol in `06-modelling.md` requires beating it on held-out data to be promoted |
| Experiment log with hypothesis, sample and decision (A2 §81) | `modelling-log.md`, append-only, negative results retained |
| H2H under strict shrinkage, experimental status (A1 dial matrix, A2 §44) | Shipped for Valentina only, shrunk by split-half reliability (0.138, so about 24% believed), measured accuracy-neutral. Advisor 1 recommends the shrinkage we already apply |
| Keep the cards negative result but distinguish propensity from counts (A2 §45) | `foul_weight = 0` with the finding retained; the cards market exists and barely beats base rate, stated as such |
| Promotion transition model with a fitted portability coefficient (A2 §41) | Built: promoted-club team priors shrunk at beta 0.373, fitted on 66 promotions since 2001 |
| ML and Bayesian challengers under strict temporal validation (A2 §89 to 90) | Planned in `18-model-roadmap.md` in the same order and with the same caveats |
| CRPS, Brier per line, reliability, ECE, bootstrap CIs (A2 §60, 92) | `backtest/metrics.py`. Missing pieces are PIT, interval coverage and segment splits, which phase 1 adds |

---

## 🛑 What we reject, and the stress-test of each rejection

### 1. A shared match-level random effect (A1 phase 2, A2 §13 to 16, 61 to 62)

Both audits call the 1.644 slope the most important unresolved problem and
prescribe a latent per-match effect. The 2026-08-23 measurement
(`25-match-variance.md`) decomposed match-total variance per character, with the
decomposition validated against planted shared factors in
`tests/test_match_variance.py`:

- The house model's predictive variance for a total (26.93) already exceeds
  what happens (24.43). Fitted shared sd: 0. Adding a random effect would widen
  a distribution that is already about 10% too wide.
- The house slope of 2.0 is a discrimination fault, not a spread fault: point
  estimates barely vary between matches. A mean-1 random effect does not move a
  point estimate, so the prescribed fix does not touch the actual defect.
- The original 1.644 was one configuration's number read as the model's. The
  slope runs 0.44 to 2.00 across characters on the same data.

**Stress-test of the pushback.** Two things keep this from being a clean
dismissal. First, the audits could not have known: 27-how-it-works still
advertises the stale number, which we fix now. Second, `25-match-variance.md`
itself records that ECE and log loss currently disagree (expansion improves one
and worsens the other), and that disagreement is entangled with the live
calibration question below. So the rejection is of the *remedy*, not of the
attention: steps 2 and 3 of the variance plan (referee estimated alongside team
effects, and modelling the total first then allocating it) stay live, and the
variance study gets re-run after the calibration re-audit lands.

Advisor 2's related point (§15 to 16) that within-match legs are correlated for
slips: for the house model the measurement says treating legs as independent is
approximately correct, which was precisely the practical worry. The caveat
printed under combination tickets stays until the calibration question settles.

### 2. Remove amplification from the core model (A1 fix 1, A2 §98 partially)

Advisor 1 reads `mean = base + (mean - base) × amplify` as an uncalibrated
distortion of the baseline. It is not in the baseline: the house parameter set
and Tayler both run `amplify = 1.0`, and the calibration correction is fitted
on house output. Amplification exists only in the four deliberately opinionated
characters, which are the product. Moving "personality downstream into
selection" is also partially the current design: selection preference functions
already differ per character.

**Stress-test of the pushback.** The defensible kernel in advisor 1's point is
real: the site publishes character probabilities with the same visual weight as
house probabilities, and a reader who takes Alan's 65% at face value is
consuming a number that was made overconfident on purpose. That sits uneasily
with the honesty commitments in `13-legal-and-ethics.md`. The right fix is
advisor 2's §34, not deletion: publish the house number next to every character
number with the deviation stated. Adopted into phase 1.

### 3. Retune the character dials toward optimality (A1 dial matrix)

Constrain Alan to k ≥ 5, cut Tayler to k = 15, and so on. Each proposed change
sands a character toward the house model, and five house models is no product.
The characters are hypotheses about temperament, and the bake-off plus a locked
evaluation period (A2 §31, 82, adopted below) is the honest control on them. If
a character's dials make it consistently and boringly wrong, the record will
show it and the record is the point.

**Stress-test.** Is "it is the product" a licence for arbitrary numbers? No,
and the constraint that keeps it honest already exists: a character may be
wrong but never deliberately stupid, and every dial is a position a real
analyst could defend. What the audits add is governance, not new dials: the
characters must never be tuned against the final test period, and their gap to
house must be reported rather than implied. Both adopted.

### 4. Scrape bookmaker internal endpoints for odds (A1 strategy A2/B)

Rejected in ADR-009 before the audits arrived, for reasons that have not
changed: terms-of-service breach, maintenance against anti-bot measures,
republication of licensed data being a worse problem than collection, the £0
rule, and this project's stated position of not using sources whose owners have
said no. Advisor 2 (§68) explicitly warns against building on undocumented
scraping endpoints, so on this point the two audits disagree and advisor 2 is
right.

The factual premise is also weaker than advisor 1 states: the free-tier APIs
named carry no player fouls market for soccer at all. The Odds API's full
soccer prop list was checked (cards, shots, tackles exist; fouls do not), and
its props come from US books. There is no free or paid archive of the UK prices
this model would need. See ADR-009 and `12-risks-and-open-questions.md`.

**Stress-test.** Market coverage changes, so a standing quarterly re-survey of
licensed fouls-prop availability is adopted rather than treating the Aug 2026
survey as permanent truth. And the machinery arguments in both audits survive
the sourcing rejection: what CAN be built at £0 is the manual capture page
(M7), the cards comparator from US books as a labelled weak signal, and CLV on
that small sample. That is phase 1's odds work.

### 5. Spatial interaction matrices (A1 fix, A2 §36 to 38 partially)

Advisor 1 wants channel-level matchup factors weighted by overlapping pitch
minutes. The data does not exist here: positional and heatmap data died with
the January 2026 Opta termination, we hold position CODES from formation lines,
and take-ons and carries are gone from every free source
(`26-data-sources.md`). Advisor 1 also slightly misreads the r = -0.003
finding: it was not "positions ignored", it was a specific test of whether
facing an exceptional foul-winner predicts anything beyond the club-level
factor, measured over 9,419 player-matches, after the team effect. It does not.

**Stress-test, and a partial concession.** A coarse version IS testable with
what we hold: formation lines place slots, so "full-back facing a formation
with wide wingers" versus "facing a narrow diamond" is a derivable channel
feature that the -0.003 test did not cover. Registered as a future study.
Advisor 2's role-over-position framing (§36) is the right lens for it, even
though the behavioural-style features they list (§37) stay blocked on data.

### 6. Live in-play modelling (A2 §96)

An explicit non-goal in `12-risks-and-open-questions.md`, and stays one until
the product changes. Noted without prejudice: the architecture (timestamped
facts, distributions, append-only predictions) would extend to it.

---

## 🚦 Phase 1: what we propose to build next

Ordered. Every model change goes through the harness and ships only on beating
the incumbent out-of-sample, per `06-modelling.md`. Studies come before ships.

### 1. The substitute programme (advisor 2 §4 to 12, 94 to 95, the centrepiece)

The best idea in either audit, and feasible with the 81,327-row player-match
file. Today a confirmed bench player collapses to a flat 50% appearance chance
and an average 22 sub minutes, which is exactly the averaging mistake the
minutes model was built to avoid, one level down.

- **1a. Dataset.** Historical substitute appearances with entry minute
  (90 minus minutes played, accepting stoppage-time noise), position, opponent,
  referee, and game state at entry approximated from the half-time score for
  second-half entries, which covers most of them.
- **1b. Study.** Sub fouls per 90 by entry window, position and HT game state.
  FoulRate_sub against FoulRate_starter, pooled and per player. Game state ×
  substitute interaction, which the three failed global game-state attempts
  never tested (advisor 2 §8 and §46 are right that a conditional effect can
  hide inside a flat aggregate).
- **1c. Model change, only if 1b finds signal.** Entry-time-conditioned
  exposure for the bench branch, a sub-specific rate adjustment, and the flat
  0.5 appearance prior refitted from data.

### 2. Calibration re-audit prework (advisor 2 §51 to 54)

The live wrong-direction flag is already in the modelling log with a
no-touching-on-282-claims discipline, which stands. What phase 1 adds is the
apparatus so that when the sample is big enough the decision is mechanical:
version the calibration table, add PIT and interval coverage to
`backtest/metrics.py`, and report calibration by segment (pre and post lineup,
starters against subs, thin against rich evidence, per line). Set the sample
threshold now, in advance, so nobody moves the goalposts later.

### 3. Thin-evidence parameter uncertainty (advisor 2 §55, 90 to 91)

A player at mean 1.2 on 3 effective matches currently gets the same
distribution width as one at 1.2 on 100. The cheap principled version: mix the
negative binomial over the Gamma posterior implied by the shrinkage
pseudo-counts, widening thin players only. The prior negative results on
widening (1.2x and 1.4x global expansion both lost) do not cover this, because
those were unconditional. Evidence-conditional widening is a different
hypothesis and gets its own harness run.

### 4. House-next-to-character publication (advisor 2 §34 to 35, resolving advisor 1's fix 1)

Show the house probability beside every character number with the deviation
quantified. Keeps the product, fixes the honesty tension, and makes boldness
measurable (deviation from the pack, which the site already defines correctly).

### 5. Odds work that is actually available (both audits, reframed by ADR-009)

Manual price capture page for tracked lines (the M7 deliverable), the
`player_to_receive_card` comparator wired as a labelled weak signal, CLV
measured on that honestly small sample, and a quarterly re-survey of licensed
fouls-prop availability. NO_MARKET_DATA stays distinct from NO_EDGE (advisor 2
§109) when this is built.

### 6. Governance and docs

Lock a final evaluation period the characters never touch (advisor 2 §31, 82).
Update `27-how-it-works.md`'s "what this does not do" to the superseded
variance measurement. Note on Bdog: his fade is a fixed constant today, so
advisor 2's out-of-fold concern (§32) does not yet bite, but the guard is
recorded in code comments so that fitting FADE ever triggers the OOF design.

---

## 💡 Future ideas, registered in `ideas.md`

In rough value order, each with its blocker stated: coarse positional-channel
matchups from formation lines; match-based rather than calendar decay for the
house half-life; manager and regime-change targeted evaluation of Alan's
claimed edge (needs a hand-maintained manager-change CSV); hurdle and
Poisson-lognormal challengers for the distribution ladder; referee effects on
distribution shape rather than mean; rest and congestion features from fixture
dates; a crude substitution-endogeneity test (starters' minutes against their
own fouls that match); within-branch minutes distributions; Kish effective
sample size alongside `effectiveMatches`; an age curve for Lily.

---

## 📊 Summary scorecard of the two audits

| | Advisor 1 | Advisor 2 |
|---|---|---|
| Already built | H2H shrinkage | Separate targets, directional opponents, margin handling, leakage controls, provenance, house model, experiment log, promotion beta, challenger plan |
| Adopted | Character-probability honesty (via labelling, not deletion), minute-dependent context (folded into the sub programme) | Substitute programme, calibration apparatus, parameter uncertainty, house-beside-character, locked eval period, conditional game-state tests, NO_MARKET_DATA distinction |
| Rejected on evidence | Shared match random effect, bivariate NB, dial retuning, endpoint scraping, spatial matrices as specified | Shared match random effect (same measurement), live modelling (non-goal) |
| Blocked on data | Interaction matrices, age curves | Role and style features, team tactical layer, full game-state-at-entry |

## 🔗 Related

- `25-match-variance.md`, the measurement that retires the audits' variance fix
- `decisions/ADR-009-fair-odds-only.md`, the odds reality both audits needed
- `modelling-log.md` 2026-08-23 entries, the live calibration flag
- `ideas.md`, where the future list above is registered with dates
