# Supabase

**One project: `foulgorithm-prod`.** See [ADR-010](../docs/decisions/ADR-010-single-database.md).

It holds the real accumulating history from day one, even though the work is developmental, so that if a separate dev copy is ever wanted at M5 no data has to move.

## Migrations

Plain SQL in `migrations/`, numbered `NNN-description.sql`. There is no migration runner and there is not going to be one.

**Apply once, by hand:**

1. Open the Supabase SQL editor.
2. Paste the migration and run it.
3. Record the applied migration number in `APPLIED.md`.

Every migration written also gets pasted into chat so it can be copied straight across without opening a file.

Migrations are append-only. To change something, write a new migration. Never edit one that has been applied.

## Protecting the track record

Almost everything here is derived and rebuildable from the raw response cache in `data/raw/`. Wiping the fact tables costs minutes, not data.

**`predictions` is the exception.** A prediction is a claim made at a moment in time, and the project's honesty commitments say predictions are never edited or deleted. Two protections:

1. **A trigger raises on `UPDATE` and `DELETE`.** Triggers are not row level security, so this binds the service role as well. Removing it means deliberately dropping the trigger.
2. **Every published prediction is also written to a git-committed JSONL log**, so the record survives independently of this database entirely.

Append-only costs nothing, because the schema already works that way: a post-lineup prediction is a new row with a different key, not an edit of the pre-lineup one.

`prediction_grades` stays mutable on purpose, since grades are derived and must be recomputable when scoring improves.

## Rules

- Row level security is enabled on every table in the same migration that creates it, never in a later one.
- Public read policies are explicit and narrow. There is no public write anywhere.
- The service role key writes from GitHub Actions only. It never appears in the site, a notebook or a commit.
- Every table that holds a fact has `known_at`, `source` and `ingested_at`. See [docs/03-data-model.md](../docs/03-data-model.md).

## Keeping the free tier alive

Free projects pause after 1 week without activity. The daily ingestion job keeps it awake during the season. An off-season gap will pause it, which needs a manual restore rather than being a data loss.
