# Fixing the settle job's schedule

**Status: Planned 2026-08-24, REVISED the same day after the scheduled job ran
and disproved half of the original diagnosis.** Self-contained: everything needed
to pick this up cold is here.

> ⚠️ **If you adopted an earlier version of this file, re-read it.** The original
> claimed the settle workflow had never run and put "prove it executes" first.
> That was wrong, and the corrected first step is the opposite of harmless: doing
> the cadence fix before it makes coverage WORSE.

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

### ~~Problem 2: it appears never to have run~~ WRONG. It runs fine.

The first draft claimed the workflow had never executed, on the evidence that
both files in `data/graded/` came from local runs. Two hours later the Monday
schedule fired and committed `bc725f9 Grade the round` as `foulgorithm-bot`:
977 graded claims, snapshot updated, track record refreshed.

Struck through rather than deleted, because the reasoning was sound and the
conclusion was wrong. Absence of evidence in a two-day-old repository is not
evidence of absence, and a whole step of work was nearly prescribed on it.

### Problem 2, the real one: snapshots taken too close to full time

That same run added three fixtures and reframed everything. Coverage now:

| Fixture | Kickoff | Coverage |
|---|---|---|
| Hull v Man United | 22 Aug **11:30** | 89% |
| Everton v Crystal Palace | 22 Aug **14:00** | **15%** |
| Ipswich v Sunderland | 22 Aug **14:00** | **0%** |
| Nott'm Forest v Leeds | 22 Aug **14:00** | **7%** |
| Brentford v Tottenham | 22 Aug **16:30** | 90% |
| Brighton v Aston Villa | 23 Aug 13:00 | 87% |
| Man City v Bournemouth | 23 Aug 13:00 | 100% |
| Newcastle v Liverpool | 23 Aug 15:30 | 97% |

**Every poor fixture sits in the same 14:00 slot.** The games either side of it
that day are fine, and two simultaneous kickoffs the next day are fine, so it is
neither simultaneity nor frequency.

The five Ipswich players that were captured all show **exactly zero fouls**.
In a 26-foul match that is not a quiet afternoon, it is a stat that had not
posted. Appearances had incremented and fouls had not, so the difference was
real, attributable, and zero.

`STATS_DELAY` in `store/players.py` is already three hours and its comment
already says full-time stats publish shortly after the whistle. It sets
`known_at` on history rows. **It does not gate when a snapshot may be taken.**
That is the bug.

## ✅ The fix

### ✅ Step 1: refuse to settle a fixture that has not settled — SHIPPED 2026-08-24

`jobs/settle.py:pending_fixtures()` plus a guard at the top of `run()`. One
refinement the implementation forced, worth recording: the guard defers the
**whole run** rather than skipping the fresh fixtures. Settling the ready ones
and snapshotting anyway would freeze the fresh one's half-posted reading into
the baseline, which is precisely the mechanism that loses the fouls. The
original wording below ("left for the next run") is what that turned out to
mean in code. `STATS_DELAY` is imported from `store/players.py` rather than
redefined. Tested, including the boundary and the not-yet-kicked-off case.

The actual bug, and the smallest fix. Before differencing, require every fixture
in the window to have kicked off at least `STATS_DELAY` ago. One that has not is
left for the next run rather than settled against half-posted stats.

**Do this before step 2.** Snapshotting more often without it makes things
worse: it raises the chance of catching a match in the window between
appearances posting and fouls posting, which is exactly what produced three
fixtures graded near zero.

Worth a test: a player whose appearances rose but whose fouls did not move, in a
fixture that finished twenty minutes ago, must not be recorded as having fouled
nobody.

### Step 2: snapshot after every matchday, not twice a week

Only after step 1, and it is a smaller problem than it first looked: six of nine
fixtures already sit at 87% to 100%. Still worth doing, because a four-day window
will eventually catch a player featuring twice, but no longer the headline.

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

1. **Refuse to settle a fixture younger than `STATS_DELAY`.** An hour, and it is
   the real bug. Doing step 2 first makes coverage worse, not better.
2. Add coverage reporting against the league's own match totals, with a failure
   threshold. An hour.
3. Generate the cron from real kickoffs, keeping Mon/Thu as a backstop. Half a
   day, with a working precedent in `jobs/schedule.py`.
4. Only then consider whether the track record needs a caveat on the site.
