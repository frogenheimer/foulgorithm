# The one-command gameweek

**Status: Planned 2026-08-24, build starting the same day.** The aim, in
Oliver's words: after each gameweek, one script updates the stats, one run
produces the next round's predictions, and one updater refreshes every
relevant area of the site, then commits and pushes, provided everything ran
successfully. Routine weeks cost a click in VSCode; sessions with a model are
for changing how the models think.

This document is the design, the reasoning behind its three hard decisions,
and the seam between what runs locally and what the bot already runs in CI.

---

## 🎯 What exists already, and what is missing

Most of the pieces are built. Every publisher is a module with a make target:
`make players`, `make predict`, `make characters`, `make export`. Settlement
runs in CI twice a week as `foulgorithm-bot` and commits its own output. The
predictions store dedupes on a natural key, so re-running a publisher is
idempotent and a crashed run can simply be re-run.

Four things are missing, and they are the whole of this plan:

1. **An orchestrator.** Nothing chains the stages, so a gameweek is currently
   five commands in the right order with no gate between them.
2. **A verification gate.** Exit code zero is the wrong test. Settle
   legitimately exits "nothing new" and now also "deferring, a match is still
   posting", and neither means the data is fresh. The gate has to interrogate
   the OUTPUT: every fixture predicted, every club resolved, inputs actually
   current.
3. **A current-season refresh for match data.** `football_data.fetch` serves
   any cached file forever, which is right for settled seasons and wrong for
   the running one. The moment `2026-27_E0.csv` first lands on disk, the match
   store freezes, and with it the live opponent factors shipped today. Found
   while designing this, not yet bitten; the refresh stage exists to make sure
   it never bites.
4. **A current calibration.** The published correction was fitted against the
   model as it was before today's two changes, both of which improved
   calibration, so the correction now likely over-shrinks. It gets refit
   against the current model before the updater goes near a publish.

## 🚦 The stages

`python -m foulgorithm.jobs.gameweek`, via `make gameweek`. Stages run in
order and the run stops at the first hard failure. Nothing is committed
unless every hard gate passed.

| stage | does | on failure |
|---|---|---|
| **refresh** | refetch the in-progress football-data season file and fixtures; the league season file refreshes inside prediction already | hard stop |
| **settle** | `jobs/settle.run()`. Exit 0 graded, 1 nothing-new-or-deferred, both fine; exit 2 means the source is dead | hard stop on 2 only |
| **predict** | `site_export`, `predict_round`, `player_round`, `character_round`, `combinations` | hard stop on `predict_round` or `player_round`; the rest report and continue, counted in the summary |
| **verify** | the output gate below | hard stop |
| **commit** | `git add` the specific published paths, one commit named for the round | hard stop |
| **push** | only with `PUSH=1` | reported |

**`DRY=1`** runs refresh, settle in its dry mode, predict and verify, then
prints what WOULD be committed and stops. Predict writes real files either
way, because they are deterministic outputs and the claims store dedupes; dry
mode's promise is only that nothing reaches git.

## ✅ The verification gate

The gate asks about outputs and inputs, never about exit codes:

- every fixture in the upcoming round has predictions, with a sane player
  count per fixture, no NaN, every probability inside (0, 1);
- the match store's newest row is recent enough for the season phase, and the
  in-progress season file was touched by this run;
- the league season file's reading is from today;
- the season-evidence report is within bounds: anomalies and unresolved
  counts at or below stated ceilings;
- the squad resolution did not collapse: resolved count at or above a floor.

Any failure prints exactly what and stops before commit. A publish that
cannot pass this gate is a publish that should not happen.

## ⚠️ The three decisions, stated so they stay decided

**Push stays behind a flag until it has earned trust.** The site is the
public track record, and its credibility rests on never quietly publishing a
bad round. The updater commits automatically and pushes only with `PUSH=1`;
after a few clean weeks of reading the summary before pushing, flip the
default. Cheap insurance against the one bad Saturday.

**One entry point, two callers.** CI's settle job and the local updater must
not become two diverging paths. The updater calls the same `settle.run()` the
bot calls; if a scheduled predict job ever lands in CI, it calls
`jobs/gameweek` itself rather than its own sequence.

**Failures are loud and partial success is named.** The cosmetic publishers
may fail without blocking a round, but every failure appears in the run
summary and the commit message says what was skipped. A summary that says
"done" while the league table silently failed is the 2025 failure mode with
better manners.

## 🧮 The calibration refit, first

Prerequisite, not a stage. `backtest/calibration_fit.py` refits the existing
correction form, `corrected = base + (raw − base) × shrink`, against the
model as it now is: season evidence attached, match-store opponent factors
on. Fit and test windows never overlap, mirroring the original discipline.
The reference file gains provenance, fitted-at, windows, n and a version, so
the correction stops being a constant of unrecorded origin. The full
distributional redesign stays where the plan of record put it: after the
pre-registered live sample, not now.

## 🔗 The seams with other work

- **Settle cadence and mins-per-match retention** stay in the settle lane
  (`33-settle-schedule.md`). One addition worth making there: settle fetches
  fouls, drawn and appearances but not `mins_played`, so the per-match rows
  it could persist for training lack minutes. One string in a tuple plus a
  snapshot migration, and every settled round becomes training-grade data.
- **FPL-Core-Insights** (live per-match player feed, surveyed in the
  modelling log) may eventually supersede season-total diffing for training
  data. In-flight elsewhere; the updater does not depend on it and gains
  silently if the store starts merging it.
- **Season rollover** is unbuilt and out of scope here. The first August run
  will need a person present.

## 📊 Offline re-runs, while we are here

Every study from the upgrade day becomes a make target, so checking a number
never again needs a session: `make study-season-totals`,
`make study-team-context`, `make study-league-pool`, `make study-dependence`,
`make study-provider-offset`, `make fit-calibration`. Each prints its tables
to the terminal and touches nothing but its own reference output.
