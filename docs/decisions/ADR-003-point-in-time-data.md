# ADR-003 — Every fact carries `known_at`

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Every fact row in the database stores `known_at`, the earliest moment its content was knowable from public information. Feature builders take an `as_of` timestamp and may only read rows where `known_at <= as_of`. Models never read the database directly.

## Context

The 2025 version's only evaluation predicted matchweeks 1 to 26 using team averages computed from files that already contained those matchweeks. It reported a win percentage that meant nothing, and nobody noticed because nothing in the data made the mistake visible.

This is the single most common way a sports model fools its author, and being careful is not a defence. It has to be structurally impossible.

## Options considered

**Filter by match date.** The obvious cheap version: only use matches played before the fixture being predicted. Rejected because it is not sufficient. Referee appointments, lineups and odds all become known at times unrelated to match dates, and a match-date filter silently lets a lineup from an hour before kickoff into a prediction made three days earlier.

**Rebuild state per prediction from an event log.** Fully correct and considerably more machinery than this project needs at 57,000 rows.

**Timestamp every fact and filter on it.** Chosen. Cheap, understandable, and it covers the non-match facts the date filter misses.

## Consequences

- Every source adapter must decide, and document, when its facts became public. This is real work per adapter and occasionally a judgement call. Conservative choices are required, meaning later rather than earlier.
- Backtests are trustworthy by construction rather than by inspection.
- Pre-lineup and post-lineup predictions become naturally separable, which turns out to be a product feature as well as a correctness one.
- Three defences layer on top: structural filtering, an instrumented read check in tests, and a canary dataset with a pure-noise target that any leaking model will beat. See [../07-backtesting.md](../07-backtesting.md).
- Historical data imported in bulk needs a documented rule for assigning `known_at`, since sources rarely tell us. Where the rule is a guess, it is a conservative guess and it is written in the adapter.
