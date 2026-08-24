# Fixing the settle job's schedule

**Status: Planned 2026-08-24, not built.** Self-contained: everything needed to
pick this up cold is here.

---

## 🎯 Why this is urgent rather than tidy

A player's fouls in one match are recoverable **only** as the difference between
two season-total snapshots taken either side of it. The league publishes running
totals and nothing else: there is no as-of-date parameter, and every gameweek
filter the API accepts is silently discarded. Verified in
[28-foul-data-sources.md](28-foul-data-sources.md).

So **per-match player data cannot be recovered backwards, ever**. Only rounds we
snapshot through will ever have it. Every week the settle job does not run is a
week of player-match data lost permanently, and no amount of money fixes it
afterwards.

That is the whole argument. It is also why this sits ahead of any modelling work.

## 🚦 What is actually wrong: two separate problems

### Problem 1: the cadence skips players

`.github/workflows/settle.yml` runs twice a week:

```
- cron: "0 9 * * 1"   # Monday 09:00
- cron: "0 9 * * 4"   # Thursday 09:00
```

`jobs/settle.py:per_match()` deliberately skips any player whose appearances did
not rise by **exactly one** between snapshots. That rule is correct: two
appearances in one window cannot be attributed to a single match, and guessing
would be worse than skipping.

But with a Monday/Thursday cadence the windows are wide:

| Window | Covers | A player featuring twice |
|---|---|---|
| Thu 09:00 → Mon 09:00 | Thu, Fri, Sat, Sun | Thursday and Sunday, skipped |
| Mon 09:00 → Thu 09:00 | Mon night, Tue, Wed | Monday and Wednesday, skipped |

Measured coverage against the league's own match totals, from
[10-weekly-review.md](10-weekly-review.md):

| Fixture | Captured | Actual | Coverage |
|---|---|---|---|
| Arsenal v Coventry | 22 | 23 | 96% |
| Brentford v Tottenham | 28 | 31 | 90% |
| Hull v Man United | 17 | 19 | 89% |
| Everton v Crystal Palace | 3 | 20 | 15% |
| Nott'm Forest v Leeds | 2 | 29 | 7% |
| Ipswich v Sunderland | 0 | 26 | **0%** |

Nothing in those numbers is false. The grades that exist are right; there are
simply too few of them in half the fixtures, and a fixture graded on five players
drags the published track record around while saying almost nothing.

### Problem 2: it appears never to have run

`data/graded/` holds two files, both written by **local** runs:

```
413b017 Fix the scheduled jobs, which would have failed on every run
804e862 Grade what we publish, and fix two bugs that would have faked it
```

No commit in the history came from a scheduled settle run. The lineup workflow
HAS fired in production (`e3e3ea0 Confirmed lineups for this round`), so the
runner and the commit permissions work. Settle specifically has not.

**Confirm this before changing the cron.** Fixing a cadence on a job that never
executes would produce no improvement and look like the fix failed. Check the
Actions tab for `settle` runs, and if there are none, find out why: a schedule
on a repository with no recent pushes gets disabled by GitHub after 60 days of
inactivity, which is the most likely cause and is invisible unless looked for.

## ✅ The fix

### Step 1: prove it runs at all

Trigger `settle` manually via `workflow_dispatch` and watch it. Success is a
commit touching `data/graded/` and `data/state/player_season_totals.json`.

If it fails, the cause is more likely credentials or a disabled schedule than
logic: the job runs clean locally.

**Do not proceed to step 2 until a scheduled or dispatched run has committed.**

### Step 2: snapshot after every matchday, not twice a week

The fixture list is known in advance and the pattern already exists:
`jobs/schedule.py` rewrites `lineups.yml`'s cron from real kickoffs. Do the same
here.

- Target: **one run roughly three hours after the last kickoff of each matchday**.
  Full-time stats publish shortly after the whistle; `STATS_DELAY` in
  `store/players.py` is already three hours and is described as conservative.
- A Premier League week typically has two to four matchdays (Fri, Sat, Sun, Mon,
  plus midweek rounds), so this is roughly three to five runs a week rather than
  two.
- Keep the Monday and Thursday crons as a **backstop**. A generated schedule that
  silently stops generating is worse than a dumb one that always fires.

Expected effect: every fixture lands in a window of its own, so the
appearances-rose-by-exactly-one rule stops excluding anyone. Coverage should move
from 0-96% to consistently near 90%, which is where the three well-covered
fixtures already sit.

### Step 3: report coverage, so a bad week is visible

The job currently reports how many claims it graded. It cannot currently say how
many it **missed**.

Add a comparison against the league's own match totals, which we already fetch:
for each settled fixture, sum the per-player fouls captured and compare with
`fk_foul_lost` from `stats/match/{id}`. Print coverage per fixture and fail loudly
under a threshold, say 60%.

Without this, a regression in cadence looks exactly like a quiet week.

## ⚠️ What this does NOT fix

- **Nothing before today.** October 2025 to now is gone at player-match level and
  stays gone.
- **The archive gap.** Feb to May 2025 and everything after 14 September 2025
  remain missing from the six-league files. This only affects what we collect
  from here.
- **The published track record stays biased** until enough evenly-covered rounds
  accumulate to outweigh the six fixtures already graded at 0% to 96%. Worth
  saying on the record page rather than waiting for someone to notice.

## 📋 Order

1. Confirm the workflow executes at all. Manual dispatch, watch for a commit.
2. Generate the cron from real kickoffs, keeping Mon/Thu as a backstop.
3. Add coverage reporting with a failure threshold.
4. Only then consider whether the track record needs a caveat on the site.

Steps 1 and 3 are each an hour. Step 2 is half a day and has a working precedent
in `jobs/schedule.py`.
