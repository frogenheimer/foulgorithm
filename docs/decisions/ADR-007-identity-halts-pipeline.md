# ADR-007 — Unresolved identities halt ingestion

**Status**: Accepted
**Date**: 2026-08-21

## Decision

When an ingestion run meets a team or player it cannot resolve to a canonical id, it raises, writes the unresolved record to a pending file for human review and stops that source's run. It never skips the record and never guesses.

## Context

Every data source spells names differently, and the differences are not systematic. `Nott'ham Forest`, `Nott'm Forest` and `Nottingham Forest` are the same club. `Gabriel Magalhães`, `Gabriel dos Santos Magalhães` and `Gabriel` may or may not be the same player depending on which Gabriel is in the squad that season.

The 2025 version joined on display names from a single source. A silent mismatch there does not throw an error, it produces a player with no history who then gets modelled as a debutant, or worse, inherits somebody else's numbers.

Fuzzy matching as a fallback makes this more likely, not less, because it turns a loud failure into a confident wrong answer.

## Options considered

**Fuzzy match with a similarity threshold.** Rejected. Two players with similar names at the same club is not a hypothetical, and the failure is silent.

**Skip unresolved records and log a warning.** Rejected. Warnings in a scheduled job are read by nobody. Skipping also biases the data in exactly the direction that hurts: new signings and fringe players are the ones most likely to be unmatched, and they are also the ones the model knows least about.

**Halt and require human confirmation.** Chosen.

## Consequences

- Ingestion breaks a few times each transfer window and each August, and someone has to add crosswalk entries. This is a handful of lines of YAML, a few times a year.
- Deterministic source ids are used wherever a source provides them, which keeps manual work to the genuine edge cases.
- Fuzzy matching still exists, but only to propose candidates for a human to confirm, never to resolve automatically. A name match alone is never sufficient: corroborating fields (birth date, club, position, nationality) are required.
- A test asserts that every row in the current snapshot resolves, so an unresolved identity cannot reach a model.
- The crosswalk files are committed to git, so identity decisions are reviewable in a diff and recoverable.
