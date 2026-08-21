# Vision and scope

**Status: Decided**

## The problem

Bookmakers price player prop markets (will this player commit 2 or more fouls, will he be booked) less carefully than they price match results. Match odds get shaped by enormous money and sharp attention. Player props get set with thinner models and lower limits, so the prices drift further from true probability.

Fouls in particular are driven by things that are measurable and reasonably stable: who plays, what position, who they face, which referee, home or away, and how the game is likely to flow. That combination is a modelling problem, not a guessing problem.

## What we are building

Three things, in this order:

1. **A data pipeline** that assembles player-level match history for the Premier League from free sources, with strict point-in-time correctness so nothing can see the future.
2. **A modelling and backtesting platform** where different algorithms compete on identical data under identical rules, and the winner is decided by calibration and simulated returns rather than by which one felt clever.
3. **A public website** that shows the predictions before kickoff, updates when official lineups land, and publishes the graded outcome of every single prediction afterwards.

## Who it is for

Someone who follows the Premier League, understands that a probability is not a promise, and wants to see the reasoning rather than be handed a tip. The tone throughout is "here is our estimate and here is how wrong we have been historically", never "lock of the week".

## Principles

- **Distributions, not tips.** Every output is a probability distribution. A user picks the line they care about.
- **Public grading.** Every published prediction gets settled and stays visible, including the bad ones. This is the entire credibility strategy.
- **Calibration before accuracy.** A model that says 60% and is right 60% of the time is more useful than one that is confidently wrong.
- **Free to run.** No paid service anywhere in the stack. This is a hard constraint, not a preference.
- **Boring beats clever.** A shrunken average that beats a neural net in the backtest ships instead of the neural net.

## Explicit non-goals

We are not building:

- **An odds comparison site.** We do not have licensed odds data and we are not going to pretend otherwise. We publish fair odds derived from our own model. Bookmaker prices, where we have them, are an input to our private value calculation, not a public product.
- **A tipster service.** No "units", no staking advice on the public site, no results screenshots.
- **A live in-play product.** Everything is pre-kickoff. In-play needs paid low-latency data and a different risk posture.
- **A multi-sport platform.** The architecture generalises, the product does not. Premier League first, and probably only, for a long time.
- **Anything that requires a Gambling Commission licence.** See [13-legal-and-ethics.md](13-legal-and-ethics.md).

## What success looks like

In order of importance:

1. The pipeline runs unattended for a full season without silently producing wrong data.
2. Published predictions are well calibrated across at least 500 settled player-market outcomes.
3. The model beats a market baseline on the subset of fixtures where we captured bookmaker prices.
4. Somebody who is not Oliver uses the site more than once.

Revenue is not on that list yet, deliberately. Access stays free until the track record justifies charging. The architecture supports a paywall from day one so that decision stays cheap.

## Relationship to the 2025 version

The original Foulgorithm lives at `~/Documents/Foulgorithm`. It is not being extended. It is a reference for the domain intuition, which was sound, and a catalogue of failure modes, which were severe: swapped venue multipliers, a look-ahead-biased backtest, silent exception handling, a truncated normal fitted to count data, and no concept of value against a price.

This rebuild keeps the intuition and fixes every one of those, structurally rather than by being more careful. See [decisions/ADR-001-rebuild-not-extend.md](decisions/ADR-001-rebuild-not-extend.md).
