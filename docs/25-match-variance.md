# The match-level variance gap, and how to close it

**Status: Diagnosed 2026-08-23, not built. This is a plan.**

Raised from an observation on one Saturday: actual totals ran 19, 20, 26, 29, 31
while we predicted 22, 24, 22, 22, 23. The predictions looked timid. They are,
but not in the way it first appears, and the difference decides what to build.

---

## 🎯 What is actually wrong

Measured over 659 matches and 16,749 player-matches:

| level | our sd | optimal sd | regression slope | verdict |
|---|---|---|---|---|
| **Player** | 0.401 | 0.404 | **1.007** | correctly scaled |
| **Match total** | 1.11 | 1.83 | **1.644** | **39% too narrow** |

A calibrated model predicts the conditional mean, so its predictions should
always vary less than outcomes. The test is not "does it vary less" but
"does it vary less than it could", and the regression slope answers it: 1.0
means correctly scaled, above 1.0 means every prediction should be pushed
further from the mean.

**Per player we are already at 1.007.** Expanding player predictions was tested
and it loses: log loss 0.4337 at no expansion, 0.4360 at 1.2x, 0.4412 at 1.4x.
Being bolder about individuals makes the model worse.

**Per match we are at 1.644.** Twenty-two correctly-scaled player predictions
sum to a total that is far too narrow.

---

## 🚦 Why the two disagree

Because the errors partly cancel in the sum. Adding up twenty-two independent
predictions produces a total whose spread is smaller than reality's, and the gap
is exactly the size of whatever moves every player in a match in the SAME
direction at once.

That shared component is missing from the model. Each player is predicted from
his own rate, his minutes and his opponent, and nothing says "this particular
afternoon was scrappy". A referee who lets things run, a derby that boils, a
pitch, a game state: all of them move twenty-two players together, and the model
treats them as twenty-two independent draws.

**This is the same shape as the dispersion mistake made twice before.** Marginal
variance is not residual variance. What differs here is that the missing
variance is real and shared, not an artefact of measuring the wrong thing.

---

## ⚠️ What has already been tried and failed

Three candidates for a shared match factor, all measured, none shipped.

| candidate | result |
|---|---|
| **Referee effect** | Deliberately excluded. A raw ratio of averages is confounded by which teams a referee was assigned, and it is exactly the number that looks like signal and is not |
| **Game state from closing odds** | Real and monotonic: favourites foul 15% below their own rate. Three attempts to use it all scored worse. Slope moves by a factor of 2.5 between periods |
| **Head-to-head history** | Real, tiny: split-half correlation +0.138, true effect about 1.06 fouls on 21. Shipped for Valentina, accuracy-neutral |

None of them is the missing variance. Head-to-head is the right SHAPE, a
per-match multiplier applied to everyone, and about a twentieth of the size
needed.

---

## ✅ The plan

In order, cheapest first. Each step is measured against match-total dispersion
AND player-level log loss, because a change that widens the total while breaking
individual calibration is not an improvement.

### 1. Fit a match-level random effect, properly

Rather than hunting for the cause, estimate the effect. A per-match multiplier
drawn from a fitted distribution, with variance set to close the observed gap:
1.644 down toward 1.0.

This is the honest version of "we know matches vary more than our players do,
and we do not know why". It widens the total distribution without claiming to
know which match will be scrappy, so combination tickets and match markets get
correct spread while individual predictions stay where they are.

**Test.** Match-total CRPS and the regression slope. Player log loss must not
move. If it does, the effect is being applied in the wrong place.

### 2. Give the referee a partially-pooled effect

Referees are the most plausible shared cause and the current treatment is to
exclude them entirely, which is right for a raw ratio and wrong as a permanent
answer. A referee effect estimated ALONGSIDE team effects, rather than as a
ratio of averages, is not confounded in the same way.

Spread across 19 referees: fouls per match 20%, fouls booked 26%. Some of that
is assignment. Estimating both at once is how to find out how much.

**Test.** Does the fitted referee variance reduce the unexplained match variance
from step 1. If the random effect shrinks when referees enter, they were part of
the answer.

### 3. Model the match total directly, then distribute it

Predict the total from team rates, referee and context, then allocate it across
players in proportion to their own rates. The total gets its own error term and
the players inherit a shared one by construction.

This is the biggest change and the most likely to work, because it puts the
shared component where it belongs instead of hoping it emerges from a sum.

**Test.** Both, plus combination-ticket calibration, which is where the current
under-dispersion does the most damage: a three-leg ticket priced from
independent legs in a scrappy match is materially wrong.

### 4. Only then consider expansion

If steps 1 to 3 leave a gap, scale what remains. Last because it is a correction
without a cause, and this project has three negative results from applying one.

---

## 📊 One number worth watching

Expanding player predictions **improves** calibration error while worsening log
loss: ECE 0.0186 at 1.0x, 0.0068 at 1.4x. That is the live under-confidence
already recorded in the modelling log showing up from the other side, and it
means the two diagnostics currently disagree.

Whatever gets built has to reconcile them rather than optimise one.
