# ADR-008 — Two Supabase projects for dev and prod

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Run two free Supabase projects, `foulgorithm-dev` and `foulgorithm-prod`, selected by the `FOULGORITHM_ENV` variable. Local work uses dev. Only GitHub Actions writes to prod.

## Context

Development needs a database that can be wiped, reseeded and broken freely. The live site needs a database that is never broken. Both need to be free.

A separate but related need is fast model iteration, which a network round trip per experiment does not give.

## Options considered

**One project, separate schemas.** Cheapest in accounts, and one mistaken command in the wrong schema takes the site down. Rejected because the isolation is nominal.

**Local Supabase in Docker.** Fully offline and genuinely isolated. Rejected for now because it adds Docker setup and daily friction on the machine, and the snapshot mechanism already solves the offline requirement for the work that matters most.

**Two hosted projects.** Chosen. The free tier permits it, isolation is real, and there is nothing to install.

## Consequences

- The store layer refuses to write to prod unless it detects a CI context or `ALLOW_PROD_WRITE=1` is set explicitly. Isolation is enforced in code, not just by convention.
- Migrations get applied by hand twice, dev first. Slightly tedious, and it means every migration is rehearsed before it touches prod.
- Free Supabase projects pause when idle. The daily ingestion job keeps prod warm. Dev pausing is harmless because experiments run against local snapshots rather than against the database.
- Model experiments read frozen parquet snapshots from `data/snapshots/`, not the database, so iteration is instant and results are reproducible. The snapshot is also what makes a backtest run today reproduce exactly next month.
- Two sets of keys to manage. `.env` locally, GitHub Actions secrets for CI, and the service role key never leaves those two places.
