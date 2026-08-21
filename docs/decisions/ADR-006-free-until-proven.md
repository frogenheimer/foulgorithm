# ADR-006 — Free access until the track record justifies charging

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Everything on the site is free. Supabase Auth ships from the first release anyway, and no payment rail is chosen or built yet.

## Context

The long-term intention is a small access fee. The question was whether to design the paywall now or later.

Two facts pushed the answer. Retrofitting authentication onto a public site is a genuinely painful rebuild, so auth should exist early. Choosing a payment provider is the opposite: the sports forecasting category is restricted or banned by several mainstream providers, the landscape shifts, and there is nothing to charge for until the model has a record worth paying for.

## Options considered

**Paywall from launch.** Rejected. Charging for an unproven model is both commercially hopeless and against the honesty principle the project is built on.

**Paywall pre-kickoff, free after settlement.** An attractive model that keeps transparency intact while making the paid product genuinely valuable. Deferred rather than rejected, and it remains the leading candidate for when charging starts.

**Free with no auth, add both later.** Rejected because of the retrofit cost.

**Free with auth from day one, payment deferred.** Chosen.

## Consequences

- Row level security policies are designed now with a paywall in mind, so switching later is a policy change rather than a re-architecture.
- Accounts have to earn their keep immediately with something users want: following teams and players, saved preferences, email alerts.
- The hosting question stays dormant until charging starts, at which point ADR-004's migration applies.
- The payment provider decision is explicitly parked. When it is made, it needs its own ADR covering provider restrictions on sports forecasting content.
- Success in the free era is measured by calibration and repeat usage, not revenue. Recorded in [../00-vision.md](../00-vision.md).
