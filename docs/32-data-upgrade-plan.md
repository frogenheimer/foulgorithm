# Feeding the new data into the models: the revised plan

**Status: Proposed 2026-08-24. Written for external review.** This document
reviews the 2026-08-24 data expansion (`28-foul-data-sources.md`,
`29-why-leagues-differ.md`, the addendum in `audit-responses/`) side by side
with the committed phase plan (`31-next-phase-plan.md`), and revises that plan.
The prove-then-build structure survives. What changes is that the build half
gains a third phase fed entirely by data now on disk, two evidence-pack items
gain teeth, and four operational fixes become prerequisites because live
evidence is currently leaking away weekly.

---

## 🎯 What changed underneath the plan

The phase plan was written against a world where player data was one frozen
81,327-row file and the league API was a settlement tool. Four days of data
work changed that world:

| Asset, all verified by fetching | Size | Span | Live? |
|---|---|---|---|
| Player-matches, six leagues | 485,569 rows, 8,968 players | 2017 to Sep 2025 | frozen |
| Official per-player season totals, 39 usable stats | 18,143 rows, 67 columns | 2006/07 to now | **yes** |
| Team match stats, ~180 per team per match | 15,200 rows, 269 columns | 2006/07 to 2025/26 | **yes** |
| Promoted-club Championship priors | 26 seasons, team level | in use | yes |

And four things did not change, stated so nobody reads this plan as solving
them: per-match player history before 2026/27 is permanently unrecoverable,
second-tier player data does not exist free, bookmaker prices remain absent,
and the only live per-match player route (API-Football) sits behind a
suspended account.

Two measured numbers govern everything below, and any model touching mixed
sources carries both:

1. **The provider offset is +4.6%.** The league API reads 3.4% to 6.4% above
   the archive on identical seasons, never once lower. Definitional, not
   error.
2. **England is the outlier among leagues.** Every other league runs 12% to
   25% above it, the gap is roughly multiplicative and roughly uniform across
   positions, and it is not explained by tackle volume
   (`29-why-leagues-differ.md`).

---

## 🚦 Side by side: what the new data does to the committed plan

| Plan item | Effect of the new data |
|---|---|
| A1 variance and discrimination | Unchanged |
| A2 calibration tables | **Amended.** The live graded sample is biased by settlement coverage, measured swinging from 96% to 0% per fixture. Coverage joins the segmentation |
| A3 joint dependence | Unchanged |
| A4 house v characters | Unchanged, plus a re-run trigger once Phase C changes the inputs |
| A5 substitute gating study | **Upgraded.** The league's events feed carries goals, bookings and substitutions with times. If it works historically, exact entry minutes and exact score at entry replace both approximations |
| A6 house selection sweep | Unchanged, runs on the England-published target. Re-run cheaply after C1 and C2 land |
| B1 substitute model | Same gate, better data behind it |
| B2 distributional calibration | Unchanged, and must be refit after C1 changes the rate input |
| B3 thin-evidence widening | **Shrinks in scope.** Season totals give most "thin" players twenty seasons of evidence; the widening applies to whoever remains thin after C1 |
| B4 house beside characters | Unchanged |
| B5 odds capture | Unchanged. No amount of this data substitutes for prices |

One new evidence-pack item:

### A7. Integrity gates for the new stores

The new data multiplies the ways the pipeline can be quietly wrong, and every
one is the class of failure this project exists to prevent. Before any model
reads the new stores: cross-league and cross-provider identity resolution runs
through the crosswalk with halt-on-unresolved (ADR-007 extended to five new
leagues and the league API's player ids); a guard test asserts the provider
offset is carried wherever archive and API numbers mix; league-offset sanity
guards (Italy near +23%, no discontinuity for a player who moved leagues); and
a double-count exclusion test proving no season contributes both archive rows
and season-total evidence to the same rate.

---

## ⚠️ Operational prerequisites, before any new modelling

These outrank model work because live evidence is being destroyed weekly.

- **O1. The settle job runs after every round, automatically, with an alert on
  miss.** A player's match fouls are the difference between two season-total
  snapshots, snapshots cannot be taken backwards, and the job has never run
  reliably. Every missed round is lost permanently. Snapshots also become
  dated files rather than one overwritten reading.
- **O2. Settlement coverage is recorded per fixture and attached to every
  graded claim**, so the track record and the calibration re-audit can weight
  or segment by it. Today three fixtures at ~90% coverage and three under 15%
  sit in one pool, and any headline accuracy number over-weights the former.
- **O3. The identity crosswalk extends to the five new leagues and the league
  API ids.** Prerequisite for C1 and C3, and it is engineering, not modelling:
  8,968 players from a second provider, with the repo rule that no name-keyed
  join exists anywhere.
- **O4. Attempt the RapidAPI route back into API-Football.** It is the only
  live per-match player foul source with a plausible free tier, the client is
  already built and tested, and the account rather than the key is what is
  suspended. If it works, per-match recency stops being a permanent limitation
  and the season-total blend in C1 becomes a fallback rather than the
  frontier. Budget-gated at £0, as ever.

---

## 🧮 Phase C: the data-fed model upgrades

Ordered by expected value against effort. Every item goes through the harness
and ships only on beating the incumbent out of sample, and every item states
its guard. The unifying idea: **the model's three inputs are the player's
rate, his minutes and his context, and two of the three went stale when the
archive froze. The new data makes all three current again, then makes two of
them richer than they have ever been.**

### C1. Un-stale the player rate with official season totals

**The single highest-value change available.** The player's own rate is the
largest input to every prediction and its per-match source stops in September
2025. The league's own season totals are current, cover twenty seasons, and
include minutes, so the missing eleven months exist as rates.

Design: season-total evidence enters the empirical-Bayes rate as additional
exposure, weighted by a fitted blend parameter, corrected by the +4.6%
provider offset, with seasons already covered by archive rows excluded
entirely (the A7 double-count gate). The old repository's snapshot patches the
Feb to Apr 2025 window as a labelled sliver. Settle-derived per-match rows
join as 2026/27 accrues. The prior ladder becomes, in order: own per-match
record, own official season rates, own foreign-league record (C3), the
promoted-club-scaled position prior shipped 2026-08-24, position prior, league
mean. Every prediction extends the existing `priorFrom` label so an estimate
never impersonates a measurement.

**Gate.** Reconstruction test: hold out a season's archive rows, feed the
model only its season totals, measure how much of the full-data log loss is
recovered. Then live 2026/27 grading. **Guard:** the blend must not move
players whose archive evidence is already rich and recent.

### C2. Make the context factors current, then behavioural

Stage one is roadmap item 9 as written: opponent and referee factors
recomputed from the match store, which is current through May 2026, ending the
absurdity of a live prediction reading a frozen file for two of its three
inputs. Provider offset carried.

Stage two is what the 269-column team store makes possible: an opponent model
built on how a side plays rather than how many fouls it concedes. Take-ons
attempted against, touches conceded in the defensive third, PPDA (computable,
median 8.7), duel and aerial volume, `fk_foul_lost` and
`attempted_tackle_foul`, all back to 2006/07. This is the defensible version
of advisor 1's matchup thinking, at team level, on data that exists.

**Gate.** Held-out log loss against the current factor. **Guard:** collinearity
with the existing opponent factor measured before anything ships, because
"real signal, worse model" has happened three times and the game-state
post-mortem showed exactly this failure shape.

### C3. Pool six leagues under a fitted multiplicative league intercept

Roadmap item 8, now unblocked because the data is on disk and the offset
structure is measured. What it buys, most valuable first: position and role
priors estimated on 5.5x the data, which sets the floor for every thin player;
records for arrivals from abroad, where 16 of the 35 players the site shows
blank already have one in the pool (Mingueza 128 matches in Spain, Sosa 110 in
Germany), thrown away every publish today; and shrinkage and dispersion
constants refit on 8,968 players instead of hand-set.

**Gate.** Must beat the England-only model on England-only held-out data,
because England is what we publish. **Guards:** fitted intercepts land near the
measured offsets; a league mover shows no discontinuity once the intercept
applies; and the rank-transfer test from `29-why-leagues-differ.md`, that a
mover keeps his rank among peers better than his rate, comes back positive
before foreign records feed anyone's price.

### C4. Role priors from style, where they beat position priors

The audit-2 recommendation (§36 to 38) registered as blocked is unblocked: the
league API carries take-ons, touches by third, possession won by third, duels
and `attempted_tackle_foul` per player per season. Cluster player-seasons into
behavioural roles, ball-winner against creator against wide dribbler, and test
role priors against position priors for thin players. `attempted_tackle_foul`
deserves its own look: a tackle that became a foul is nearly the mechanism the
model predicts.

**Gate.** Thin-player held-out log loss, role against position. If roles do
not beat positions there, they do not ship anywhere.

### C5. The fouls-drawn upgrade

Drawn is the market we model worst, and the drawn-relevant stats are the
cheapest addition in the survey: `final_third_entries` and `pen_area_entries`
are one backfill command each, and `fouled_final_third`,
`touches_in_opp_box` and `total_contest` are already fetched. Attacking
volume features for the drawn model, tested market by market.

**Gate.** Drawn-market log loss and calibration, separately reported, which
the evidence pack requires anyway.

### C6. The hierarchical Bayesian challenger, now with a league level

Already planned; the data work changes its economics, as
`18-model-roadmap.md` records. 485,569 rows across six leagues is the regime
where partial pooling earns its fit time, league slots in above team and
position, and the posterior gives per-player uncertainty that would subsume B3
entirely if it wins. Run as a challenger against the C1-to-C4 incumbent, never
as a default.

### C7. One retry at match-total discrimination, with genuinely new features

The open question from `25-match-variance.md` gets its first new inputs since
three failed attempts: possession, PPDA, tempo and territory proxies per match
back to 2006/07. Expectations stated low, because most match spread looked
irreducible, and the three failures all began as "real signal". A bounded
study, not a commitment.

---

## ✅ Sequencing

1. **O1 to O4** immediately. Ops first because evidence decays weekly.
2. **Phase A evidence pack** as committed, with the A2 and A5 amendments and
   A7 gates. The pack measures the incumbent before the inputs change.
3. **C1 and C2 stage one**: the staleness fixes, the largest wins per line of
   code.
4. **C3, C4, C5** in that order, each behind its gate.
5. **C2 stage two, C6, C7** as challengers.
6. **Phase B unchanged throughout**: the substitute model on its upgraded
   study, distributional calibration refit after C1, widening for whoever
   stays thin, house-beside-character, odds capture.

## 📊 What this should achieve, stated honestly

Quantified where possible, hypothesis where not:

- Two of three prediction inputs stop being eleven months stale (C1, C2). The
  size of the gain is measurable in the C1 reconstruction test before
  anything ships.
- 16 players currently published with no record get real ones, and roughly
  three quarters of each promoted squad graduates from one shared number to
  club-scaled, then style-informed, priors (C3, C4, on top of the shipped
  promoted-club prior).
- The prior floor for every thin player is estimated on 5.5x the data (C3).
- The drawn market, currently the weakest, gets its first features that
  describe attacking volume rather than defending (C5).
- The substitute programme, the audit cycle's centrepiece, runs on exact entry
  times and score states if the events verification lands (A5).
- The track record stops being computed on a coverage-biased sample (O1, O2).

None of it changes what the project cannot claim: no prices, no value claims,
calibration as the primary measure, per ADR-009.

## 🔗 Related

- `28-foul-data-sources.md`, the survey every number here rests on
- `29-why-leagues-differ.md`, the league offset exploration
- `31-next-phase-plan.md`, the committed plan this revises
- `audit-responses/2026-08-24-data-addendum.md`, the blocker retired
- `18-model-roadmap.md`, items 8 and 9, which Phase C absorbs
