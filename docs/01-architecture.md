# Architecture

**Status: Decided**

## Shape

Two runtimes that never talk to each other directly. Python does all the thinking and writes its conclusions to Postgres. The website reads Postgres. That separation is what keeps hosting free and the site fast.

```
   free data sources
          |
          v
  +---------------+     raw responses cached to disk, content addressed
  |   sources/    |---> data/raw/  (gitignored, replayable, never re-fetched)
  +---------------+
          |
          v
  +---------------+     every fact tagged with known_at
  |  identity/    |---> canonical team_id / player_id via crosswalk
  +---------------+
          |
          v
  +---------------+
  |    store/     |---> Supabase Postgres (dev project or prod project)
  +---------------+
          |
          +-----------------------------+
          |                             |
          v                             v
  +---------------+            +------------------+
  |   features/   |            |    snapshot      |  frozen parquet for
  |  (as_of aware)|            |  data/snapshots/ |  reproducible experiments
  +---------------+            +------------------+
          |                             |
          v                             v
  +---------------+            +------------------+
  |    models/    |<---------->|    backtest/     |  walk-forward, leakage-checked
  |  (registry)   |            +------------------+
  +---------------+                     |
          |                             v
          v                     model_runs table + runs/ artifacts
  +---------------+
  |   publish/    |---> predictions table (keyed by model_id + version)
  +---------------+
          |
          v
  +---------------+
  |   review/     |---> grades predictions, writes weekly_reviews
  +---------------+
          |
          v
     Supabase  <----- read by ----->  Next.js site (Vercel)
```

## Components

### `sources/`
One adapter per data source. Each adapter has a single job: fetch raw bytes and return them, plus parse those bytes into typed rows. Fetch and parse stay separate so parsing can be re-run against cached responses without touching the network.

Every response gets written to `data/raw/{source}/{yyyy-mm-dd}/{hash}.{ext}` before parsing. This makes local development offline-capable, makes parser bugs replayable, and means a source going down does not stop work.

### `identity/`
Maps source-specific team and player identifiers onto canonical ids. Nothing downstream ever joins on a name. Covered in [04-identity-resolution.md](04-identity-resolution.md).

### `store/`
Thin repository layer over Postgres. Upserts on natural keys so every job is idempotent and safe to re-run. Chooses the dev or prod database from an environment variable, and refuses to write to prod unless explicitly told to.

### `features/`
Turns stored facts into model-ready rows. Every function takes an `as_of` timestamp and may only use facts whose `known_at` is at or before it. This is the single most important rule in the codebase.

### `markets/`
Declarative definitions of what we predict: fouls committed, cards, tackles. Each carries its settlement rule, its distribution family and its line grid. Adding a market should not require touching the model or backtest code.

### `models/`
A registry of competing algorithms behind one interface. Each returns a probability distribution. Covered in [06-modelling.md](06-modelling.md).

### `backtest/`
Walk-forward evaluation with hard leakage checks, scoring every registered model on identical data.

### `publish/`
Writes predictions for upcoming fixtures to Postgres, tagged with model id, version and the timestamp the prediction was made.

### `review/`
Grades published predictions after matches settle, recomputes rolling calibration and returns, writes the weekly review record. Covered in [10-weekly-review.md](10-weekly-review.md).

### `site/`
Next.js App Router application. Reads Supabase through the JS client using the anon key, protected by row level security. No server-side secrets, no API routes that do heavy work, nothing Vercel-specific so the app stays portable to Cloudflare Pages if hosting needs to change.

## Scheduling

GitHub Actions runs everything on cron. Nothing runs on a server we maintain.

| Job | Schedule | Purpose |
|---|---|---|
| `ingest-daily` | Once daily, early morning | Refresh completed match data and stats |
| `ingest-referees` | Weekly, midweek | Referee appointments for the coming round |
| `predict` | After referee appointments land | Generate and publish predictions for upcoming fixtures |
| `matchday` | Windowed, on match days | Poll for official lineups, republish predictions for confirmed starters |
| `review` | Monday morning | Grade everything, write the weekly review |
| `freshness` | Daily | Check every source produced data recently, alert if not |

The matchday job runs as one long-lived process per match window rather than many short jobs, because Actions bills per started job and short frequent jobs waste the free allowance.

## Environments

Two Supabase projects, selected by `FOULGORITHM_ENV`:

- `dev` for all local work. Wipeable, reseedable, never trusted.
- `prod` for what the public site reads. Only GitHub Actions writes to it.

Local development never touches prod. The store layer raises an error if it detects a write to prod outside a CI context unless `ALLOW_PROD_WRITE=1` is set explicitly.

## Why not a single Python web app

A Python web app (FastAPI, Streamlit, Django) would collapse this to one runtime, which is simpler. It gets rejected because free hosting for always-on Python is scarce and slow, cold starts on free tiers are painful, and the interactive front end we want is far easier in React. Splitting compute from serving keeps both halves on generous free tiers.

See [decisions/ADR-002-two-runtime-split.md](decisions/ADR-002-two-runtime-split.md).
