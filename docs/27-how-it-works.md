# How it works

**Status: Describes what is built, as of 2026-08-23.**

`06-modelling.md` describes the ladder we intended to climb. This describes the
thing that is running. Where the two disagree, this one is right.

Two passes at the same content: the short version, then the full one. The short
version is what the site's methodology page should say. The full version is what
you need before changing any of it.

---

## The short version

We are answering one question per player per match: **how many fouls will he be
involved in, and how likely is each number?**

Four things go into it.

1. **How often he fouls.** His own record, per 90 minutes, with recent matches
   counting more than old ones. A player with little history gets pulled toward
   what players in his position usually do, and the less we have on him, the
   harder he gets pulled.
2. **How long he will play.** Separately worked out, because a rate per 90 tells
   you nothing about a single match until you know whether he is starting. We
   estimate the chance he starts, the chance he comes off the bench and the
   chance he does not play at all, then treat those as three different matches
   and add them up.
3. **Who he is playing.** Some opponents draw fouls out of people. That is a
   multiplier on his own rate.
4. **Who is refereeing.** Some referees give more. Another multiplier.

That produces an average, and around the average we put a **spread**, because
the honest answer to "how many fouls" is never one number. From the spread we
read off the probability of 1 or more, 2 or more, 3 or more, and convert each
into fair odds.

Then five characters look at exactly the same evidence and disagree about it.

---

## 🎯 The full version

### The core calculation

Every prediction runs the same five steps. The characters change the dials, not
the steps.

#### 1. Rate: what this player does, per 90 minutes

```
              Σ(fouls × w)  +  k × prior
rate  =  ──────────────────────────────────
            Σ(nineties × w)  +  k
```

- `w = 0.5 ^ (age_in_days / half_life)`. A match from one half-life ago counts
  half as much as one from today.
- `prior` is the average rate for players in his position, falling back to the
  league average when we do not know his position.
- `k` is the shrinkage strength, expressed in ninety-minute equivalents. `k = 8`
  means "before I believe your own record, show me eight full matches of it".

This is empirical Bayes shrinkage, and it is the fix for the single worst flaw
in the 2025 version, which let a player with 4.6 ninety-minute equivalents top
the rankings on noise. A player with two appearances now sits almost exactly on
his position's average, which is the honest thing to say about him.

`effectiveMatches`, the number quoted on the site as evidence, is `Σw`: how many
matches of *undecayed* evidence the weighting is really standing on. A player
with 40 matches and a 60-day half-life can have an effective total under 1.

#### 2. Minutes: two stages, not an average

Averaging a rotation player's minutes produces a number he never actually plays.
Someone who starts half the time and is unused the rest averages 45 minutes and
plays 0 or 90.

So it splits:

| Branch | Probability | Minutes |
|---|---|---|
| Starts | `p_start` | his average when starting |
| Off the bench | `p_sub` | his average when substituted on |
| Does not play | `p_unused` | zero, and zero fouls |

Each is estimated from his last 12 appearances, time-decayed, with a weak prior
(`k = 2`, toward 55% start / 20% bench) so one appearance does not imply
certainty. A player with no history at all is assumed a typical starter, 70/20/10,
with the uncertainty carried as a **thin evidence** flag rather than as a low
number: returning nothing for him is how a promoted club once showed a quarter of
Manchester United's fouls.

**A confirmed lineup collapses stage one entirely.** Once the team sheet is out,
`p_start` is 1 or 0 and there is nothing to estimate. Pre-lineup and post-lineup
predictions are graded separately and never pooled, because they are different
products with different accuracy.

#### 3. Context multipliers

```
mean  =  rate × (minutes / 90) × opponent × referee
```

- **Opponent factor.** How much this opposition inflates the fouls conceded
  against them, time-decayed, expressed as `1 + (raw - 1) × opponent_weight`.
  The weight scales the *deviation*, so 0.4 means "I half believe the matchup"
  and 1.6 means "I believe it and then some". A promoted club has no top-flight
  record, so it falls back to its second-tier evidence rather than shrugging at
  1.0, which is the failure this project exists not to make.
  This lookup resolves the club name first. It did not, once: fixtures say
  "Man United" and history says "Manchester United", so it found nothing and
  returned 1.0, reading as "perfectly average" rather than "not found". Around
  half the league was affected and the discarded adjustments were not small,
  United 0.84 and Tottenham 1.25.
- **Referee factor.** Partially pooled toward the league average, never a raw
  ratio of averages: a referee's raw fouls-per-game is confounded by which
  fixtures he was assigned.
- **Head-to-head factor.** Only Valentina reads this. Some pairings genuinely
  produce more than either side's record implies, and the effect is small and
  noisy, so it is shrunk hard using split-half reliability.

#### 4. Amplification

```
base  =  position_prior × (minutes / 90)
mean  =  base + (mean - base) × amplify
```

`amplify` pushes a prediction further from, or closer to, what an ordinary
player in that position would do. Above 1 exaggerates; exactly 1 leaves it
alone. This is the dial that makes a character overconfident on purpose.

#### 5. Distribution

A **negative binomial** with `variance = mean × dispersion`. Counts, not a
truncated normal: the 2025 version used a normal on a count, which has the wrong
support and unreliable tails, and the tails are the entire thing we bet on.

Dispersion is a **constant**. A count-dependent version was fitted and measured:
the slope came out at 0.014 and moved the 3+ bias from -0.0149 to -0.0145, which
is noise. The hypothesis that a fat tail on low-mean players caused the observed
overconfidence was simply wrong, and the code was deleted rather than kept.

#### 6. Convolution across the minutes branches

Each branch gets its own negative binomial, and they are mixed by their
probabilities. The unused branch is not a small number, it is a certainty of
zero.

This matters because it puts a real spike at zero for a rotation risk. A single
smooth distribution averages that spike away, and it is exactly what a 1+ bet
settles on.

#### 7. Calibration correction

Published probabilities are corrected against measured bias before they leave
the building. The raw numbers overstate the high lines, in the direction that
makes a bad bet look good.

---

## 🚦 Where the five branch off

**All five run the code above.** There is no separate model per character at the
player level; there are five parameter sets over one model, plus one feature only
Valentina reads. That is deliberate: it makes the bake-off fair. If they used
different machinery you could not tell whether a character won because his
temperament was right or because his code was better.

The rule that keeps it honest: **a character may be wrong, but never
deliberately stupid.** Every setting below is a position a real analyst could
defend.

| | Alan | Lily | Valentina | Tayler | Bdog |
|---|---|---|---|---|---|
| **Emotion** | Anger | Lust | Violence | Terror | Bravery |
| **Half-life (days)** | 70 | 1200 | 400 | 1000 | 300 |
| **Shrinkage `k`** | 3 | 8 | 6 | 30 | 2 |
| **Opponent weight** | 1.3 | 0.5 | 1.6 | 0.4 | 1.1 |
| **Dispersion** | 1.00 | 1.10 | 1.05 | 1.25 | 1.02 |
| **Amplify** | 1.3 | 1.1 | 1.15 | 1.0 | 1.2 |
| **Head-to-head** | no | no | **yes** | no | no |

Read down the columns and the temperaments fall out of the numbers.

- **Alan (Anger)** has a 70-day memory and barely shrinks. The last two months
  are the only months, averages are excuses, and his dispersion of 1.00 is the
  narrowest of the five: overconfidence, on purpose. His edge is genuine regime
  change, a new manager or an injury crisis, which he spots before anyone. His
  weakness is that three rough games look like transformation to him and are
  usually variance.
- **Lily (Lust)** remembers for 1200 days, because reputations stay seductive
  long after they stop being true, and weights the matchup at 0.5, the second
  lowest. She prices the name over the fixture. Her edge is fixtures where
  profile genuinely drives intensity; her weakness is reputation lag.
- **Valentina (Violence)** is the only one who asks a different question rather
  than the same one more loudly. Opponent weight 1.6, the highest, and she alone
  reads head-to-head. The Merseyside derby runs about 2% above what Everton and
  Liverpool are worth separately and she is the only one who notices.
- **Tayler (Terror)** shrinks with `k = 30`, ten times Alan's, and carries the
  widest distribution at 1.25. Everything sits near the league average and he
  never exaggerates: `amplify` is exactly 1. He is the house model, the one to
  quote when a single number is wanted. He will be the best calibrated and among
  the least useful, because a prediction indistinguishable from the average is
  barely a prediction.
- **Bdog (Bravery)** shrinks least of all, `k = 2`, so he trusts thin evidence
  the others pull away from. Someone has to be first on a genuinely changed
  player. At match level he goes further and computes what the other four
  believe, then deliberately shades away from it.

### One difference that is not a dial

Selection. Every character builds a slip at each odds tier from the same pool,
and **temperament shows in which players get picked, not in picking easier
bets**. The preference function per character:

| Character | Wants |
|---|---|
| Alan | Distance from the pack, then the raw rate |
| Lily | The biggest raw numbers |
| Valentina | The strongest matchup, then some distance from the pack |
| Tayler | Agreement with the others, and volume of evidence |
| Bdog | Distance from the pack, and tolerance for thin evidence |

Boldness is defined as **deviation from the pack, not low probability**. A
character backing a 70% shot the others price at 55% is being bold. One backing
a 45% shot everybody agrees on is just accepting a longer price. Getting this
backwards would have made "bold" mean "picks worse bets", which is not a
temperament, it is a handicap.

### Match level, where they genuinely differ

At match level (total fouls in a fixture) the five are separate model classes
with different mechanisms rather than one model with five dials:

- **Alan** amplifies every deviation from the league mean by 1.35.
- **Lily** adds a glamour term, proxied by how long each club has been in the
  division.
- **Valentina** computes an aggression reading from both clubs' card records and
  bends the estimate 45% of the way toward it.
- **Tayler** shrinks with a prior of 45 matches and a referee prior of 60.
- **Bdog** fits the other four, takes their consensus and steps 40% away from it
  from his own starting point. He is the only one whose view depends on what the
  others think, and he costs four extra fits every refit.

Valentina's match model is on version 2 for a documented reason. Version 1
modelled cards alone and converted to fouls with a fitted ratio, and finished
**worse than predicting the league average**: 0.6505 log loss against 0.5993.
Cards are a noisy proxy that has been drifting away from fouls for two decades,
fouls falling 19.6% since 2000 while cards rose 16.3%. The finding stands in
`modelling-log.md`. Version 2 keeps her lens without discarding the evidence,
which is what a competent analyst with her temperament would actually do.

---

## ⚠️ What this does not do

Stated plainly, because a methodology page that only lists strengths is
marketing.

- **No bookmaker prices.** No free archive of historical player prop odds
  exists, so we cannot measure closing line value on the market we actually
  publish. Calibration on a large sample is the substitute, and it is weaker.
- **Match totals barely discriminate.** The 39% under-dispersion originally
  reported here was one configuration's number: re-measured per character on
  2026-08-23, the house model has no missing shared variance and its total
  spread is already about 10% too wide. The real fault is that its point
  estimates barely vary between matches. Measurement and what survives of the
  plan in `25-match-variance.md`.
- **Position on the pitch does nothing.** Measured at r = -0.003 for positional
  pairings. The pitch view lets you move players around; the model does not care
  where they stand.
- **Cards add nothing.** Blending a card model in scored 0.4314 against a base
  rate of 0.4336, so the weight is set to zero and the negative result is kept.
- **Game state adds nothing**, across three attempts. The first explanation
  offered for this was collinearity with the existing features, which was
  plausible and false: measured correlation was -0.044.
- **The calibration correction may be pointing the wrong way.** Live results
  suggest the model is currently *under*-confident, saying 6% where 14% landed,
  while the correction assumes overconfidence. Too few settled claims to act on,
  and flagged here rather than quietly left.

---

## 🔗 Related

- `06-modelling.md`, the ladder as designed
- `modelling-log.md`, every experiment including the ones that failed
- `04-identity-resolution.md`, why joining these sources is its own module
- `07-backtesting.md`, how any of this gets promoted
- `25-match-variance.md`, the open problem
- `26-data-sources.md`, where every number comes from
