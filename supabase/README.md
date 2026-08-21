# Supabase

Two projects, `foulgorithm-dev` and `foulgorithm-prod`. See [ADR-008](../docs/decisions/ADR-008-two-supabase-projects.md).

## Migrations

Plain SQL in `migrations/`, numbered `NNN-description.sql`. There is no migration runner and there is not going to be one.

**Apply by hand, dev first:**

1. Open the Supabase SQL editor for `foulgorithm-dev`.
2. Paste the migration, run it, confirm it worked.
3. Repeat against `foulgorithm-prod` only once dev is proven.
4. Record the applied migration number in `APPLIED.md`.

Every migration written also gets pasted into chat so it can be copied straight across without opening a file.

Migrations are append-only. To change something, write a new migration. Never edit one that has been applied.

## Rules

- Row level security is enabled on every table in the same migration that creates it, never in a later one.
- Public read policies are explicit and narrow. There is no public write anywhere.
- The service role key writes from GitHub Actions only. It never appears in the site, a notebook or a commit.
- Every table that holds a fact has `known_at`, `source` and `ingested_at`. See [docs/03-data-model.md](../docs/03-data-model.md).

## Keeping the free tier alive

Free Supabase projects pause after a period without activity. The daily ingestion job keeps prod awake as a side effect. Dev pausing does not matter, because local experiments run against parquet snapshots rather than the database.
