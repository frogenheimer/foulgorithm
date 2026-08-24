# The final plan

**Status: Plan of record, 2026-08-24.** Consolidates the committed phase plan
(`31-next-phase-plan.md`), the data upgrade revision (`32-data-upgrade-plan.md`)
and both external reviews of 32. This document owns the execution order and the
release gates; 31 and 32 stay as the reasoning trail. Where this document and
either of them disagree, this one wins.

Both advisors approved the direction of 32. Advisor 2 scored it 8.5/10 on plan
quality and 7/10 on statistical readiness, and asked for the evidence gates to
become hard release gates. Advisor 1 raised four risks, two of which survive
scrutiny and are folded in below. The consolidated verdict both converge on:
**the danger is no longer missing data or missing method, it is that an
expanded dataset multiplies the ways to manufacture apparent signal.** This
plan is built around that.

---

## 🎯 The governing principle

Adopted from advisor 2's review, nearly verbatim, as the rule every item below
answers to:

> **New data is an opportunity, not evidence of improvement. Every new source
> must first prove incremental information against the frozen incumbent, under
> the same temporal and integrity controls, before it is allowed to change a
> production prediction.**

And the four boundaries that stay standing whatever ships:

1. No historical bookmaker prices means no demonstrated betting edge. The
   public claim stays "calibrated forecasts" (ADR-009).
2. Live coverage is currently biased, so no strong live-calibration conclusion
   is drawn until O1 and O2 land.
3. Match-level discrimination remains an open research question. C7 is bounded
   research, never a solved problem.
4. Aggregate and match-level sources are never treated as independent evidence
   without an explicit overlap test.

---

## 🚦 What the two reviews changed, disposition by disposition

### Advisor 2 (statistical review): adopted almost whole

| Ask | Disposition |
|---|---|
| C1 four-way evidence design and per-player-season accounting | Adopted, in the C1 spec below |
| Validate the +4.6% offset by stat, league, position and season before using it | Adopted. The correction takes whatever form the measurement supports |
| C3 gate wording: foreign data must earn England improvement after transformations fitted on permitted history only | Adopted verbatim |
| Rank-transfer test promoted to a formal validation metric | Adopted, with its table |
| C2 feature timing rule and conditional-information ablation gate | Adopted. `known_at` discipline applies to team features exactly as to player data |
| C4 five-condition bar, position stays the default | Adopted |
| C5 promoted ahead of C4 | Adopted. Target-specific with a clear mechanism beats exploratory clustering |
| C6 challenger spec frozen before it runs | Adopted |
| C7 split into H1 totals, H2 player-level, H3 dependence | Adopted |
| Observation-level source provenance in the architecture | Adopted, the `priorFrom` philosophy extended to every measurement |
| A7 becomes a hard release gate, plus A7.5 and A7.6 | Adopted |
| A8 to A11 added to the evidence pack | Adopted |
| Complexity budget with a formal experiment record | Adopted |
| The not-yet list (no neural model, no role proliferation, no weather or narrative features, no character expansion, no live-performance model selection yet) | Adopted |
| Next deliverable is results, not prose | Adopted. See the closing section |

### Advisor 1 (architectural review): two hits, two merges, two rejections

| Claim | Disposition |
|---|---|
| Season totals collapse recency and break the decay machinery | **Adopted, their sharpest point across three rounds.** C1 now dates every piece of season-total evidence; see the spec |
| A flat +4.6% scalar distorts tails and over-corrects high-volume foulers | **Merged into the offset measurement.** As stated it conflates a multiplicative rate correction with an additive count shift; whether the definitional gap is proportional, additive or volume-dependent is exactly what the validation measures, and the correction takes the measured form. Their proposed "Poisson intensity rate difference" IS a multiplicative intensity ratio for a rate model, so the disagreement is smaller than it reads |
| 269 team features invite overfitting; demand dimensionality reduction | **Merged into C2's gate**: pre-registered small feature families, regularisation, conditional-information ablation. No kitchen sink |
| Coverage weighting should be inverse-probability weighting, not just stratification | **Adopted as a sensitivity analysis.** Their framing overstates the bias mechanism (coverage is set by snapshot timing, not by match properties), but IPW beside stratified reporting is cheap and worth having |
| League intercepts should be league x position from the start | **Rejected as the default, kept as the test.** The measured gap is roughly uniform across positions (16% to 23%), so intercept-first is right and the interaction must earn its parameters. Both 32 and `29-why-leagues-differ.md` already said test-not-assume |
| Role priors constrained at k >= 10 | Direction adopted (roles enter under heavy shrinkage), the arbitrary constant not. Fitted, like every other constant |
| CLV blindness restated | No change. The boundary is formal, no compliant route was offered, and O4 remains the only live lead |

---

## ✅ Standing rules, upgraded

1. **A7 is a hard release gate.** No Phase C model reaches production without
   passing: cross-provider identity resolution with halt-on-unresolved,
   provider-offset propagation, league-offset sanity, double-count exclusion,
   **A7.5 source exclusivity** (the same underlying match cannot enter twice
   under different provider ids) and **A7.6 aggregate reconstruction** (where a
   season total and its archive rows coexist, the aggregate relationship is
   proven before either enters a blend).
2. **Every measurement carries provenance**: provider, stat definition,
   competition, season, `known_at`, and whether it is aggregate or
   match-level. The empirical-Bayes machinery must never weigh twenty
   season-total observations as if they were twenty match observations.
3. **The complexity budget.** Every experiment records hypothesis, new degrees
   of freedom, data used, evaluation window, incumbent, metric, improvement
   with uncertainty, and the ship or reject decision, in the modelling log,
   hypothesis stated before the validation result is seen. The log already
   works this way by culture; it is now a rule.
4. **No headline live number without its coverage distribution**: claims,
   fixture and player coverage, unresolved counts, and coverage-stratified
   scores beside the headline, with an IPW-weighted figure as sensitivity.
5. **Challengers run frozen.** C6 in particular: feature set, hierarchy,
   priors, tuning budget and evaluation window fixed before the first fit.
6. **The not-yet list stands**: no neural models, no role taxonomy beyond what
   C4's gate admits, no weather, media or narrative features, no new character
   sophistication, and live performance is not a model-selection criterion
   until O1 and O2 have run for a stretch.

---

## 📋 Execution order

> 📌 **Progress, 2026-08-24.** Shipped so far: the provider-offset measurement
> (which found no offset, plus a 75-match archive hole and a pagination
> truncation), PIT and interval coverage in the metrics module, the C1 season
> total blend (78% of the stale-year gap recovered), C2 stage one opponent
> factors (ECE down 23% and 31% under production conditions), the A3
> dependence tripwire, and step 1 of the settle fix. Full working in the
> modelling log under 2026-08-24.

| Priority | Item | Gate |
|---|---|---|
| **P0** | O1 settle cadence and immutable snapshots (`33-settle-schedule.md`, extended below). **Step 1 shipped 2026-08-24**; cadence and immutable records outstanding | Runs after every round; anomaly alerts live |
| **P0** | O2 coverage-aware grading | Coverage attached to every graded claim |
| **P0** | O3 cross-provider, cross-league identity | Zero unresolved identities, halt otherwise |
| **P0** | O4 RapidAPI route back to per-match data | Attempt and record. £0 gate |
| **P0** | A7 integrity gates incl. A7.5, A7.6 | Pass/fail results, not descriptions |
| **P0** | A1 to A6 evidence pack on the incumbent | Published before any input changes |
| **P1** | C1 season-total rate blend | Reconstruction test, spec below |
| **P1** | C2 stage one, current opponent and referee factors | Held-out log loss, offset carried |
| **P1** | C3 six-league pooling | England-only improvement, transfer matrix, rank test |
| **P1** | C5 fouls-drawn features | Drawn log loss and calibration per line |
| **P1** | A5/B1 substitute study then model | Gating study first, exact timings if events verify |
| **P2** | C4 behavioural role priors | Five conditions, heavy shrinkage on entry |
| **P2** | C2 stage two, behavioural opponent model | Family ablation, regularised |
| **P2** | C6 Bayesian challenger | Frozen spec |
| **P2** | C7 match discrimination retry | H1, H2, H3 separately scored |
| **P2** | B2 distributional calibration | After C1 changes the rate input |
| **P3** | B3 widening for whoever stays thin, B4 house-beside-character, B5 odds capture | As committed in 31 |
| **P3** | Character work beyond A4's contingency | Deprioritised |

---

## 🧮 The redesigned item specs

### O1, extended

The cadence fix is planned in `33-settle-schedule.md` and this plan adopts it
wholesale, plus advisor 2's two additions: the settlement record becomes
immutable (snapshot timestamp, player, team, season, cumulative totals,
source, source timestamp, delta, coverage status, run id), and alerting fires
on anomalies, not just failures: an implausibly unchanged snapshot, collapsing
player counts, a decreasing cumulative total, unusually low coverage, or an
identity-resolution drop.

### C1, the full evidence design

The season-total blend is the highest-value change and gets the strictest
test. Three design rules, then the gate.

**Every piece of season-total evidence is dated.** Preferred: disaggregate a
season total across the player's actual appearance dates, recoverable from the
league's historical team lists, as uniform-intensity pseudo-exposure that the
existing decay machinery treats like any other dated evidence. Fallback where
appearance dates are not recoverable: date the block at its season midpoint.
Undated aggregate blocks never enter the rate, which answers advisor 1's
recency objection structurally rather than with a discount constant.

**Aggregation still costs something.** A fitted discount applies to
disaggregated pseudo-exposure relative to true match rows, because uniform
intensity is an assumption, and the discount is fitted, not guessed.

**The offset is measured before it corrects anything.** Provider divergence
tabulated by stat, league, position, season and player volume decile, with an
explicit test of multiplicative against additive form. The correction ships in
whatever form the measurement supports.

*Resolved 2026-08-24, first item off this plan:* the measurement ran and the
form question dissolved. Matched player by player, the ratio is 1.0002, flat
across seasons, volume and position; the +4.6% was a composition artifact of
the API fouls table omitting zero-foul players. The blend reads
`data/reference/provider_offset.json` and applies what it finds, which is
currently nothing. The same study exposed a 75-match archive hole in April to
May 2022 and a pagination truncation in the season fetch, both now repaired.
Modelling log, 2026-08-24.

**Gate.** Per-player-season accounting (source, matches represented, exposure,
overlap, eligibility), then four models compared on identical held-out data:
archive-only, season-totals-only, combined, and the full-data oracle where it
exists. Log loss, CRPS, Brier and calibration per line. The combined model
must beat archive-only **because it holds new information**: on player-seasons
where the archive is already complete, combined and archive-only must be
statistically indistinguishable, which is the direct test that no double
counting survived.

### C3, hardened

Single multiplicative intercept first, per the measurement. League x season
and league x position interactions tested before the architecture freezes,
never assumed in either direction. The England gate in advisor 2's words:
foreign data is never allowed to improve England predictions merely by
increasing sample size; it must improve England out-of-sample scoring after
all provider and league transformations are fitted only on permitted
historical data. The rank-transfer test becomes a formal metric with its own
table: for every league mover, rank before and after, raw rate transfer,
league-adjusted transfer, and predicted against actual post-move rate. A11's
transfer matrix (England to England, others to England, pooled to England,
England to others) is the summary judgement.

### C2, C4, C5, C6, C7, deltas only

- **C2**: every candidate feature answers "what was known, when, from which
  matches" before it is computed; families are pre-registered and small;
  N = 38 matches per team-season is the binding constraint and regularisation
  is mandatory; the gate is conditional incremental information (incumbent,
  incumbent plus feature, plus family, full), with bootstrap intervals.
- **C4**: ships only if role priors beat position priors on thin-player
  held-out log loss, preserve calibration, stay stable across seasons,
  transfer to unseen players and survive a sample-size control. Roles enter
  under heavy fitted shrinkage toward position.
- **C5**: promoted above C4. Reported at 1+, 2+ and 3+ drawn separately,
  because a count-distribution improvement need not be uniform across lines.
- **C6**: frozen spec before first fit, and if its posterior uncertainty wins,
  it subsumes B3.
- **C7**: three hypotheses scored separately: better match-total
  distributions, better player-level discrimination, better within-match
  dependence. The third reconnects to the pairwise-correlation test in A3.

### The evidence pack, final composition

A1 to A6 as amended in 32, plus: **A7** as the hard gate with A7.5 and A7.6,
**A8** a source contribution matrix for every production feature (source,
coverage, known-at, aggregate or match, incremental gain), **A9** an evidence
duplication audit per player-season (which observations actually move the
posterior), **A10** a feature-family ablation from player-history-only up to
the full model, showing where improvement actually comes from, and **A11** the
cross-league transfer matrix.

---

## 📦 The next deliverable

Both advisors said the same thing and they are right: no more prose. The next
thing they see is the evidence pack, containing at minimum the C1
reconstruction result, the provider-offset validation tables, the C3 transfer
matrix and rank-transfer table, the C2 family ablation, the C5 per-line drawn
result, A7 pass/fail results, and the A8 source contribution table. Every
number with its interval and n, every table reproducible from a manifest.

## 🔗 Related

- `31-next-phase-plan.md` and `32-data-upgrade-plan.md`, the superseded-for-execution reasoning trail
- `33-settle-schedule.md`, the O1 plan this adopts and extends
- `28-foul-data-sources.md` and `29-why-leagues-differ.md`, the data ground truth
- `audit-responses/`, the full correspondence with both advisors
- `decisions/ADR-009-fair-odds-only.md`, the claim boundary
