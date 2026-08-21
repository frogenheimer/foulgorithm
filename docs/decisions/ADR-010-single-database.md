# ADR-010 — One database, with predictions made append-only

**Status**: Accepted
**Date**: 2026-08-21
**Supersedes**: [ADR-008](ADR-008-two-supabase-projects.md)

## Decision

Run **one** Supabase project. Protect the only genuinely irreplaceable data with a database-level append-only rule on `predictions`, plus a git-committed copy of every published prediction. Revisit splitting into dev and prod at M5, when a public site actually exists.

## Context

ADR-008 chose two projects for isolation. The friction it creates is real and lands on a solo side project: every migration applied by hand twice, two sets of keys, both free-tier slots consumed with nothing spare, and two databases to keep from pausing.

Re-examining what the isolation actually protects changed the answer.

**Almost all of the data is derived and rebuildable.** Every source response is cached to `data/raw/`, ingestion is idempotent upserts, and features and grades are computed from facts. Wiping the fact tables is an annoyance measured in minutes, not a loss.

**One table is genuinely irreplaceable: `predictions`.** A prediction is a claim made at a moment in time. Deleting it destroys the track record, which is the project's only real asset, and the honesty commitments say predictions are never edited or deleted.

So the risk is not "the database" at all. It is one table. Protecting a whole second database to guard one table is the wrong shape of solution, and it happens to be the expensive one.

**There is also no site yet.** Milestones M1 to M4 have no public reader. Isolation protects nobody until M5.

## Options considered

**Keep two projects.** Real isolation, and it pays a permanent friction cost from day one to protect against a risk that does not exist until M5. Rejected.

**Two schemas in one project.** Rejected in ADR-008 as nominal isolation, and that reasoning still holds.

**Local Postgres in Docker for dev.** Genuine isolation and migrations could be scripted locally, so manual SQL happens once. Rejected because Docker friction on the machine is exactly the kind of drag that kills side projects, and it solves a problem we do not have yet.

**One project, protect the one table that matters.** Chosen.

## Consequences

- **Migrations get applied once.** This was the actual complaint and it goes away.
- **One set of keys**, and one free-tier slot stays spare.
- **`predictions` becomes append-only at the database level**, via a trigger that raises on `UPDATE` and `DELETE`. Triggers are not row level security, so this binds the service role too. Removing the protection means deliberately dropping the trigger, which is a decision rather than an accident.
- **Append-only costs nothing**, because the schema is already append-only by design: a post-lineup prediction is a new row with a different key, not an edit of the pre-lineup one.
- **Every published prediction is also written to a git-committed JSONL log.** This makes the track record recoverable independently of the database, and in a public repository it doubles as timestamped evidence that a prediction existed before kickoff. That is not the independent proofing CAP guidance asks of paid tipsters, but it is far stronger than a mutable database row. See [../13-legal-and-ethics.md](../13-legal-and-ethics.md).
- **`prediction_grades` stays mutable**, deliberately. Grades are derived from predictions and outcomes, so they must be recomputable when scoring improves.
- **Local mistakes can still wipe fact tables.** Accepted, because they rebuild from the raw cache.
- **Revisit at M5.** When a public site exists, splitting is a two-minute project creation plus one replay of the accumulated migrations. Nothing about this decision makes that harder.

## Practical note

Use the project named `foulgorithm-prod` as the single database, even though the work is developmental. It accumulates the real history, so when a dev copy is eventually wanted, `foulgorithm-dev` becomes the scratch copy and no data ever has to move.
