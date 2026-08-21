# Development workflow and cost budget

**Status: Decided**

Two constraints shape everything here: iteration has to be fast, and the running cost has to be exactly zero.

## The loop

The design goal is that everyday work happens locally, offline, in seconds, and nothing in the cloud runs while you develop.

**Model and pipeline work**

```bash
make snapshot        # freeze current dev database to data/snapshots/{id}.parquet
make backtest        # run registered models against the snapshot, write report
make test            # pytest
```

Experiments read the frozen snapshot from disk. No network, no database round trips, no cloud compute. A backtest over 5 seasons of roughly 57,000 player-match rows is a laptop-scale problem, so iterations take seconds to a couple of minutes.

**Ingestion work**

Every fetch writes its raw response to `data/raw/` before parsing. Re-running a parser replays from disk and never re-hits the source. This matters twice over: it keeps iteration instant, and it keeps us well inside rate limits on sources that are hostile or capped.

```bash
make ingest SOURCE=fbref --cached   # parse only, no network
make ingest SOURCE=fbref            # fetch and parse
```

**Site work**

```bash
make site        # next dev against the dev Supabase project
```

Hot reload locally. Zero Vercel builds while iterating. Vercel only builds on push to `main`, and preview deployments stay off to save build minutes.

## Environments

| | dev | prod |
|---|---|---|
| Supabase project | `foulgorithm-dev` | `foulgorithm-prod` |
| Written by | You, locally | GitHub Actions only |
| Read by | `next dev` | The live site |
| Data | Wipeable, reseedable | Trusted |

`FOULGORITHM_ENV` selects the project. The store layer refuses to write to prod unless it detects a CI context or `ALLOW_PROD_WRITE=1` is set explicitly, so an absent-minded local run cannot corrupt the live site.

## Cost budget

Every line here is a free tier, with allowances verified on 21 August 2026. If any component threatens to exceed its allowance, that is a design bug to fix, not a bill to pay.

| Service | Free allowance | Expected use | Headroom |
|---|---|---|---|
| GitHub Actions, **private** repo | **2,000 min/month** | Roughly 200 to 300 min/month | Comfortable. Note a **public** repo gets unlimited minutes |
| Supabase | **2 active projects**, 500 MB database, 5 GB egress | Tens of MB | Storage fine. The project limit is exactly our dev and prod, with nothing spare |
| Vercel Hobby | 100 GB transfer, 45 min per build, 100 deploys/day | Low, mostly static | Comfortable. **No monthly build-minute quota exists** |
| API-Football | **100 requests/day, 10/min** | Roughly 25/week live | Fine live, tight for backfill |
| The Odds API | 500 credits/month | Occasional snapshots | Barely used, see [ADR-009](decisions/ADR-009-fair-odds-only.md) |

**Actions minute discipline**

Billing counts started jobs and rounds up, so many tiny scheduled jobs waste the allowance faster than a few long ones. Matchday lineup polling therefore runs as one job holding a loop for the pre-kickoff window, not as a cron firing every 10 minutes.

If 2,000 minutes ever binds, **making the repository public is the cheapest lever** and it costs nothing but the decision. Public repos get unlimited Actions minutes on standard runners. Given the project publishes its methodology anyway, this is worth considering on its merits rather than treating it as a last resort.

**Supabase constraints, both sharper than assumed**

- The **2-project limit applies across every organisation** where you are an owner or administrator. It is not per organisation, so it cannot be multiplied by making more orgs. Dev and prod use both slots exactly. Paused projects do not count.
- Free projects **pause after 1 week of inactivity**. The daily ingestion job keeps prod warm during the season. An off-season gap will pause it, so plan for a keep-alive or accept a manual restore each August. Dev pausing is harmless because experiments run against local snapshots.

**API-Football budget**

100 requests a day is generous for live operation (roughly 25 a week) and restrictive for backfill, where one season costs around 380 requests, so 4 days. Historical loading is a slow background activity, not a one-off import. Cache permanently: a settled match is never fetched twice.

**The rule**

Any change that introduces a paid dependency, or that materially increases scheduled compute, gets flagged before it is written. Not after.

## Tooling

- **Python 3.11**, managed with `uv` for speed. A `requirements.lock` keeps CI reproducible.
- **pytest** for tests, written before implementations.
- **ruff** for linting and formatting, run by pre-commit.
- **Make** as the task runner, because it is already installed and everything is one word.

## Git conventions

- Small commits, specific paths, never `git add .`.
- No `Co-Authored-By` lines.
- Never push without asking.
- Branch for anything non-trivial, and keep `main` deployable at all times since `main` is what Vercel builds.

## Secrets

`.env` locally, gitignored, with `.env.example` committed as the template. GitHub Actions secrets for CI. The Supabase service role key never appears in the site, in a notebook or in a commit. The site only ever uses the anon key.
