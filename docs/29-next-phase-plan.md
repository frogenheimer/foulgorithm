# Next phase: prove, then build

**Status: Proposed 2026-08-23, after both advisor replies to
`28-external-audit-review.md`. This operationalises and supersedes the phase 1
sketch in 28.**

Both advisors replied to our responses (`audit-responses/`). Advisor 1 accepted
every disposition and added nothing new. Advisor 2 scored the response 8/10 and
the underlying methodology 6.5 to 7, accepted the direction, and pressed three
challenges hard. This document takes a position on each challenge, then lays
out the phase as two halves: **Phase A proves what we have asserted, Phase B
builds on whatever survives the proof.** Advisor 2's closing request was "don't
send more prose, send an evidence pack", and that request is correct, so the
evidence pack IS Phase A.

---

## 🎯 What advisor 2's critique changes, tested before accepting

Each point below was stress-tested rather than swallowed. Where the pushback on
their pushback survived, it is stated.

### 1. "Retired by measurement" was too strong. Accepted.

Their distinction is right: our decomposition shows the specific
shared-random-effect explanation is unsupported, and that is all it shows. It
does not establish that the remaining match-level spread is unpredictable, and
"model variance already exceeds actual" does not by itself exclude a shared
factor masked by overstated idiosyncratic variance cancelling against missing
positive covariance. The planted-factor tests validate the decomposition
machinery, not that assumption.

The language changes to theirs: *the shared-random-effect explanation is not
supported by the current variance decomposition; match-level discrimination
remains an explicit open research question.* And the masking possibility gets a
direct test that does not route through the decomposition at all: measure
observed pairwise within-match residual correlation between players. If those
correlations sit near zero, independence stands on direct evidence. If they run
positive, something is cancelling and the decomposition's zero is hiding it.
The existing `pairing_study.py` does not answer this (it tests player quality,
not residual dependence), so this is new work, in the evidence pack.

### 2. Calibration is red/amber, not "apparatus pending". Accepted.

We had classed calibration as "adopted apparatus, wait for sample". Advisor 2
is right that this undersells two live problems. First, the correction may be
compensating for structural misspecification rather than measuring bias, and a
per-line shrink applied to threshold probabilities is the wrong object when the
model produces a full count distribution. Second, ECE improving while log loss
worsens under expansion is not a footnote, it is an unresolved model-selection
conflict and gets named as such. Calibration status is **red/amber** until the
evidence pack's calibration tables exist and the pre-registered sample
threshold passes. Distributional calibration replaces per-line shrinkage as the
target design for the re-audit.

### 3. "Already built" needs evidence, not assertion. Accepted.

A fair reading of our response is that it proves engineering claims well and
statistical claims thinly. Numbers quoted without their evaluation tables
(the 0.373 promotion beta, "16% worse", the H2H reliability) are assertions
until the tables are visible. Phase A produces them.

### 4. The House model must be statistically selected, not a designated character. Accepted, with one correction.

The correction first: at player level House is already its own
personality-independent parameter set (half-life 400, k = 6, opponent weight
1.0, dispersion 1.05, amplify 1.0), and Tayler is a separate character. Our
own response invited the conflation by labelling the match-level table "house
(Tayler)", because at match level Tayler's configuration currently doubles as
the reference. That conflation is real at match level and their deeper point
stands at both levels: House's dials are partly hand-picked and partly fitted,
and "a defensible default" is not "a statistically selected baseline". Phase A
includes a House selection sweep, walk-forward, locked period untouched, frozen
and recorded as an ADR. Tayler then becomes conservative *relative to House*
rather than House by designation.

### 5. The substitute model must respect information-at-prediction-time. Accepted, and worth making explicit.

Their warning: the study dataset uses realised entry minutes and realised
half-time scores, and none of that is knowable at kickoff. The production
design is therefore the mixture

    P(F) = sum over t of P(T = t) x sum over g of P(G = g | T = t) x P(F | t, g)

where the study estimates the conditional rates P(F | t, g) from history, and
the pre-match model supplies the distributions over entry time and game state.
Realised states never enter a prediction. The harness's `known_at` discipline
enforces this mechanically, but the design intent is now stated rather than
implied. Their classification is adopted as the gate: this is a research
programme, and it does not become a production model until the gating study
says the complexity earns its keep.

### 6. Character selection rules are model selection. Accepted as a standing rule.

Any rule that uses historical performance to choose among characters,
parameters or selection strategies is itself model selection and must be
evaluated out-of-sample on the locked period. This generalises the Bdog OOF
guard to the whole character ecosystem.

### 7. The commercial claim boundary. Already formalised; pointed to rather than re-adopted.

Advisor 2 asks that the project formally downgrade its claim from "identifies
betting value" to "produces calibrated foul forecasts". That boundary already
exists in ADR-009 ("we cannot make systematic value claims, and we will not")
and in `13-legal-and-ethics.md`. Nothing new to build; the evidence pack's
cover note will state the boundary so no reader mistakes calibration evidence
for value evidence.

### Where we hold our ground

- **No obligation to implement the Poisson-lognormal model.** Advisor 2
  concedes this themselves. The open question survives; the specific remedy
  stays retired unless the pairwise-correlation test reopens it.
- **The substitute programme stays in the phase** rather than waiting behind
  the P0 proof work, because it shares no dependency with the calibration or
  variance questions. Advisor 2's ordering concern is honoured differently:
  nothing from the substitute work *ships* before its gating study, and the
  gating study itself sits inside the evidence pack.
- **Advisor 1's synthesis** required no changes: it accepts every disposition.
  One silent correction to their restated roadmap: substitute context
  multipliers are gated on the study finding signal, not committed.

---

## 🚦 Phase A: the evidence pack

One artefact, versioned in the repo, produced by harness runs rather than
prose. Every table names its dataset, window, n and metric definitions. The
cover note states the ADR-009 claim boundary.

### A1. Variance and discrimination

Per character per season: n, observed variance of totals, mean predicted
variance, fitted shared sd, regression slope with its exact definition stated
(OLS of observed totals on predicted means), sd of predicted means, sd of
outcomes, correlation of predicted mean with outcome, RMSE, log score and
CRPS. Plus the reconciliation advisor 2 asked for: the original 1.644 and the
new numbers recomputed on one identical dataset, with both formulas shown, so
the revision is auditable rather than asserted.

### A2. Calibration, before and after correction

Per line (1+, 2+, 3+, 4+), split by pre-lineup and post-lineup, starter and
substitute, thin and rich evidence, committed and drawn: calibration slope and
intercept, ECE, PIT histogram, interval coverage, and log loss before and
after the correction. PIT and coverage get added to `backtest/metrics.py`
first (tests first, per repo rule). The ECE-against-log-loss conflict gets its
own named section with the expansion sweep numbers.

### A3. Joint dependence, directly

Observed pairwise within-match residual correlation, teammates and opponents
separately. Predicted against observed joint hit rates for 2-leg and 3-leg
same-match combinations, and calibration of combination tickets as priced
under independence. This is the direct test of the masking concern in point 1
and the honest audit of the caveat printed under every slip.

### A4. House against the characters on the locked period

Lock the evaluation period first, then: House and all five characters, raw and
calibrated, on log score, CRPS, Brier per line and ECE, per market. The pack
states plainly which model wins on log score and CRPS, not only ECE.

### A5. The substitute gating study

The question that gates Phase B item 1: is substitute foul behaviour different
enough from starter foul behaviour, by entry window, position and half-time
game state, to justify entry-time machinery? Includes the game state x
substitute interaction our three global game-state failures never tested.

### A6. House selection sweep

Walk-forward sweep over the House dials (half-life, shrinkage, opponent
weight, dispersion), locked period untouched, winner frozen as House and
recorded in an ADR. The match-level reference configuration gets its own
identity in the same pass, ending the Tayler conflation.

---

## 🚦 Phase B: build on what survives

Every item gated on Phase A output and on beating the incumbent in the
harness, per `06-modelling.md`.

1. **Substitute model change**, only if A5 finds signal: entry-time
   distribution for confirmed bench players, sub-specific rate adjustment, the
   flat 0.5 appearance prior refitted, production form as the mixture in
   point 5 above.
2. **Calibration redesign**, only after A2 and the pre-registered sample
   threshold: distributional calibration replacing per-line shrinkage,
   versioned, trained on data the model never fit on.
3. **Thin-evidence widening**: Gamma-posterior mixture over the shrinkage
   pseudo-counts, widening thin players only. Prior negative results were
   global expansions and do not cover this.
4. **House beside every character number** on the site, deviation quantified.
5. **Manual odds capture page** for tracked lines, the cards comparator wired
   as a labelled weak signal, CLV on that sample, quarterly re-survey of
   licensed fouls-prop coverage.

## ✅ Standing rules adopted this phase

- The locked evaluation period exists before A4 runs and nothing tunes on it.
- Character selection rules are model selection and are evaluated
  out-of-sample.
- No realised in-match state ever enters a pre-match prediction; substitute
  predictions marginalise over entry time and game state.
- Calibration is never fitted on outcomes the model trained on, and its
  version is recorded with every prediction batch.
- The public claim stays "calibrated forecasts", never "betting value",
  until CLV evidence exists on captured prices (ADR-009).

## ⚠️ Exit test for the phase

The evidence pack exists in the repo with every table reproducible from a
manifest; the variance language in 25, 27 and 28 matches the agreed phrasing;
the House ADR is written; and either the substitute model shipped through the
harness or the gating study's negative result is recorded in the modelling log
with the same prominence a positive one would have got.

## 🔗 Related

- `28-external-audit-review.md`, the review both advisors replied to
- `audit-responses/`, the correspondence
- `25-match-variance.md`, which gains the agreed phrasing
- `decisions/ADR-009-fair-odds-only.md`, the claim boundary
- `ideas.md` 2026-08-23 entries, everything valuable that is not in this phase
