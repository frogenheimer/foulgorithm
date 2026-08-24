# Foulgorithm response to the adversarial counter-audit

**Date:** 23 August 2026
**Responding to:** "Critical Counter-Audit: Exposing the Flaws in the Developer Defense"
**Prepared by:** the Foulgorithm project

An adversarial pass is welcome and this one changed the plan in two places: the
odds capture protocol and a character calibration contingency, both now in
`31-next-phase-plan.md`. The other two claims are rejected, and the rejections
rest on identifiable technical errors in the counter-audit rather than on
preference. Taking the four in order.

---

## 1. The slope argument gets the statistics backwards, in three places

**The counter-audit's claim:** slope 2.003 means the house model is "radically
over-confident and systematically miscalibrated", the slope "flipped from
under-dispersed (1.644) to massively over-dispersed (2.003)", and the model
"severely overpredicts extreme match totals".

**What the slope actually is.** It is the OLS regression of observed match
totals on predicted means. A slope of 1.0 means the point estimates are
correctly scaled. Above 1.0 means predictions vary LESS than they should and
would need expanding away from the mean. Both 1.644 and 2.003 sit on the same
side of 1.0. Nothing flipped. The move from 1.644 to 2.003 is more of the same
fault, point estimates too compressed, not a reversal into its opposite.

**Over-confidence is the wrong direction on both axes.** On the mean axis,
slope 2.0 is under-discrimination: predictions that barely distinguish one
match from another, which is timidity, not confidence. On the spread axis, the
house model's predictive variance for a total (26.93) exceeds observed
variance (24.43), which is a distribution slightly too WIDE. An over-confident
model has distributions too narrow. A 10% excess also does not support
"severely overpredicts extreme totals"; it mildly over-weights tails.

**On "we did not solve match-level variance": agreed, and we never claimed
it.** Our stated finding is that the fault is discrimination, and the agreed
phrasing on record since the second advisor's review is that match-level
discrimination remains an explicit open research question. The counter-audit
is attacking a victory declaration that does not exist in our documents.

**On correlated players within a match.** Two things the counter-audit's
argument misses. First, shared observable drivers already move all 22 players
together in the model: every player in a fixture is conditioned on the same
referee factor and the paired opponent factors. The open question is latent
residual dependence beyond those, not whether a card-happy referee affects
everyone, which the model already expresses. Second, "fundamentally flawed
regardless of single-variable slope measurements" is a refusal to let
measurement settle an empirical question, and that is not a mode of argument
this project accepts from itself or anyone else. The scheduled test is also
stronger than the one the counter-audit implies: direct pairwise within-match
residual correlation between players, which does not route through the
variance decomposition and cannot be masked by cancellation. If it comes back
positive, the Poisson-lognormal architecture is first back on the table, and
that conditional reopen is already recorded in `ideas.md`. Bivariate negative
binomial for two players generalises poorly to 22 in any case; the latent
log-normal factor is the right family if dependence shows up.

**Disposition: rejected.** The demand is already covered by a better-designed
test than the assertion behind it.

---

## 2. "Immediate multiplier resequencing" prescribes a fix with no measured size

**The counter-audit's claim:** step 3 multiplies rates by opponent and referee
factors "before accounting for minutes", so an 80th-minute substitute gets a
multiplier "meant for a full 90-minute environment", and production is
"actively generating mathematically invalid expected values" today.

**"Before" is not a thing in a product.** The mean is
rate x (minutes / 90) x opponent x referee. Multiplication commutes; there is
no sequence to fix. The substantive claim underneath is real and is the one we
accepted in the first exchange: the factors are estimated from full matches
and assume a constant per-minute effect, and late-game windows may differ.

**Why "immediate" is the wrong prescription.** Conditioning the factors on
minute windows requires estimating minute-conditioned factors from data, which
IS the substitute study, sitting in Phase A, not deferred to someday. Shipping
a correction now means shipping a guessed constant with no measured effect
size or direction. This project has shipped exactly that class of change three
times, all three made the model worse, and all three are in the modelling log.
The counter-audit asserts the current approximation is biased without offering
a sign, a size or any evidence; our graded live sample (282 claims) shows a
global under-confidence pattern, not a substitute-specific one.

**One mitigating fact the counter-audit missed.** A player's rate is estimated
from his own appearances. A habitual substitute's per-90 rate is computed
almost entirely from late-game minutes, so his rate already reflects the
late-game environment. The approximation error concentrates on players who
mix starts and bench appearances, which narrows the affected set and is
precisely what the gating study measures.

**Disposition: rejected as stated.** The work is scheduled, gated and
harness-tested. An ungated production change on an unmeasured bias is the
failure mode this repository exists to prevent.

---

## 3. "Alan's output is mathematically wrong" assumes a single true model

**The counter-audit's claim:** publishing character probabilities beside the
house number abdicates modelling responsibility to the user, and personalities
must exist strictly as selection and staking filters downstream.

**On "mathematically wrong".** Alan's 65% against house's 48% is a forecast
under different stated assumptions: a 70-day memory and weak shrinkage. It is
very probably worse calibrated, and whether it is, and by how much, is exactly
what the locked-period evaluation (A4) measures and publishes per character.
"Wrong" as a mathematical fact presupposes there is one true model and we hold
it, which is not a position a forecasting project gets to take.

**On the staking-filter remedy, which has a compliance problem the
counter-audit did not check.** This project's public site publishes no staking
advice, no unit sizes and no bankroll strategy, as a responsible-gambling
commitment recorded in `13-legal-and-ethics.md`. Moving personality out of
probabilities and into staking criteria would surface temperament as exactly
the content we have committed not to publish. Persona as a probability with
the objective baseline printed beside it is the safer construction, not the
evasion.

**What we adopt from the charge anyway.** The accusation "knowingly publishing
uncalibrated math" is testable, so we made it a tested contingency: if a
character's locked-period calibration fails a threshold stated before the run,
that character gets either a per-character calibration layer on its published
probabilities, which keeps temperament in rankings and selection while fixing
gross bias, or louder opinion labelling. That is now in the plan. What we will
not do is delete the mechanism ahead of the measurement.

**Disposition: remedy rejected, charge converted into a measured contingency.**

---

## 4. The manual odds critique is half right, and the half that is right changed the plan

**The counter-audit's claim:** manual logging produces a tiny, biased,
statistically meaningless sample, and without automated CLV the backtest stays
blind.

**What is right.** Selection bias is the real danger: a human logging lines
they find interesting produces a sample of interesting lines. Accepted, and
the capture page is now specified against it: the tracked line set is chosen
by a pre-registered rule per round rather than by attractiveness, both sides
of a line are captured where displayed, every capture is timestamped, and
discretionary additions are recorded as discretionary.

**What is wrong.** "Meaningless" overstates it on three counts. CLV needs far
fewer observations than profit does, which is the entire reason it is the
metric of choice on small samples, and every reported number carries its
interval and n by house rule. The cards comparator is automated through a
licensed API, so one market gets a systematic sample that exercises the whole
CLV pipeline end to end. And the counter-audit offers no compliant
alternative: its original proposal was scraping bookmaker internal endpoints,
which stays rejected on terms, maintenance and the £0 constraint, a rejection
the counter-audit does not contest so much as decline to mention. A small
honest sample with stated limits beats no sample, and it beats a large sample
we are not permitted to have.

**Disposition: protocol hardening adopted, conclusion rejected.**

---

## Summary

| Counter-audit claim | Disposition | Ground |
|---|---|---|
| Slope 2.003 proves radical over-confidence | Rejected | Slope direction misread, dispersion conflated with discrimination, both numbers on the same side of 1.0. The open question it gestures at is already scheduled with a stronger test |
| Immediate multiplier resequencing | Rejected | Multiplication commutes; the real fix needs minute-conditioned estimates, which is the Phase A study. Ungated corrections with unmeasured size failed three times on record |
| Personas must become selection and staking filters | Rejected, contingency adopted | "Mathematically wrong" assumes a single true model; the staking remedy collides with the responsible-gambling commitments. Per-character calibration or louder labelling now hangs on the locked-period measurement |
| Manual odds capture is meaningless | Half adopted | Pre-registered rule-based capture protocol adopted against selection bias. The meaninglessness conclusion rejected: CLV is the small-sample metric, the cards path is automated, and no compliant alternative was offered |

The adversarial pass earned its keep twice, on the capture protocol and the
character contingency. On the other two items the counter-audit argues against
positions we do not hold, using statistics that do not hold either.
