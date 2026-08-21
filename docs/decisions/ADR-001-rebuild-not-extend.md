# ADR-001 — Rebuild rather than extend the 2025 codebase

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Start a new repository rather than refactor the 2025 Foulgorithm at `~/Documents/Foulgorithm`. Keep the old code as a read-only reference for domain intuition.

## Context

The 2025 version worked in the sense that it produced output every week. A review found the output could not be trusted:

- Venue multipliers were read from the wrong team in both main calculation paths, so every player prediction used the wrong home or away adjustment for one side.
- The big-game multiplier was applied twice in the cards calculation.
- Bare `except` blocks turned every failure into a neutral multiplier, so broken lookups were indistinguishable from genuinely average fixtures.
- The only evaluation predicted matchweeks using season averages that already included those matchweeks, so its reported win rate was meaningless.
- A truncated normal was fitted to count data, with variance derived by concatenating two teams' match logs and then scaled by the square of stacked multipliers. The published "60% lines" were not 60% lines.
- Data was keyed on display names from one source, with no identity layer.
- Season identifiers and around 140 URLs were hard-coded, so the whole thing broke annually.
- The scraper no longer works at all: FBref returns 403 to this style of access as of August 2026.

## Options considered

**Refactor in place.** Rejected. The problems are structural, not local. Point-in-time correctness, identity resolution and the model interface all have to exist before the calculations can be trusted, and every one of them changes the data flow. Refactoring toward that endpoint is a rewrite performed slowly, while carrying the old bugs.

**Keep the data, rewrite the code.** Partially adopted. The historical CSVs are useful for cross-checking a rebuilt pipeline, but they are not the system of record because their provenance and timing are unknown.

**Rebuild.** Chosen. The domain knowledge transfers, the code does not.

## Consequences

- We lose nothing of value, because the only asset was the intuition and that is written down in [../06-modelling.md](../06-modelling.md).
- The first working prediction is further away than a patch would be. Accepted, because a patch produces numbers we cannot defend.
- The old repository stays untouched so the previous outputs remain available for comparison.
- Every failure listed above becomes a structural rule in the new design rather than a thing to be careful about. Careful was already tried.
