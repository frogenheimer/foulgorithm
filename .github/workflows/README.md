# Scheduled jobs

All compute runs here. There is no server.

Not built yet. Landing across milestones M2 and M4. See [docs/11-roadmap.md](../../docs/11-roadmap.md).

## Planned jobs

| Workflow | Schedule | Purpose | Milestone |
|---|---|---|---|
| `test.yml` | On push and pull request | Lint and test | M1 |
| `ingest-daily.yml` | Daily, early morning | Refresh completed match and player data | M2 |
| `ingest-referees.yml` | Weekly, midweek | Referee appointments for the coming round | M2 |
| `freshness.yml` | Daily | Check every source produced data, alert if not | M2 |
| `predict.yml` | After appointments land | Publish pre-lineup predictions | M4 |
| `matchday.yml` | Match days, windowed | Poll for lineups, republish post-lineup predictions | M4 |
| `review.yml` | Monday morning | Grade, diagnose, write the weekly review | M4 |

## Minute discipline

Actions bills per started job and rounds up, so many short jobs waste the free allowance faster than a few long ones.

**`matchday.yml` therefore runs as one job holding a polling loop across the pre-kickoff window**, not as a cron firing every 10 minutes. A cron every 10 minutes across a Saturday card would burn the monthly allowance for no benefit.

Every workflow sets a `timeout-minutes` so a hung job cannot drain the budget.

## Rules

- Secrets come from GitHub Actions secrets. Never inline, never echoed to logs.
- Scheduled writes to the database happen from here. There is one database, and `predictions` is append-only at the database level, so a re-run cannot damage the track record. See [ADR-010](../../docs/decisions/ADR-010-single-database.md).
- Jobs are idempotent. Re-running one is always safe.
- A failing scheduled job alerts via Telegram. A silent failure is the thing we are most trying to avoid.

## lineups

Watches for confirmed elevens and republishes when they land. The Premier League
publishes them at T-60.

**Cron only starts the job; it does not do the timing.** A 30-minute cron catches
T-60 somewhere between T-60 and T-30, and GitHub's scheduler runs late under
load, sometimes by 15 minutes or more. Stacked, a fixture could publish at T-15
or be missed, and tightening the interval does not help because the jitter is in
the scheduler rather than the interval.

So the job works out when the next lineups are due, sleeps until T-75, then polls
every minute until they arrive. One run covers a whole afternoon and the windows
overlap, so there is no gap between them.

Measured: our own predicted eleven is 62.9% accurate. A confirmed one is exact.
That gap is why this is worth doing properly rather than approximately.

**This lives here rather than on the site on purpose.** The site is a static
export with no backend, so there is no server for a button to call. Adding one
would mean paying for serverless invocations, or exposing a public endpoint that
anyone could use to hammer the Premier League API on our behalf. Neither works at
a budget of zero.

Exit codes matter: 0 published, 1 nothing changed, 2 the source is dead. Only 2
fails the run, because a dead source must be loud. Publishing predicted elevens
while labelling them confirmed would be the worst failure available to us.

Run it by hand from the Actions tab with `workflow_dispatch`, or locally with
`python -m foulgorithm.jobs.lineup_watch`.
