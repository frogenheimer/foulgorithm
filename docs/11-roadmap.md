# Roadmap

**Status: Decided**

Build order matters more than build speed. Each milestone produces something verifiable, and nothing depends on a component that has not been proven.

The governing principle: **the boring infrastructure comes first, the model comes late, the site comes last.** Reversing that order is how the 2025 version ended up with an unverifiable model.

## M0 — Foundations (done)

Repository, documentation, decision records, project skeleton, dev tooling. No behaviour.

## M1 — Historical data and the backtest spine

The first milestone that needs no accounts, no API keys and no scraping.

- football-data.co.uk loader: **26 seasons of match-level fouls, cards and referees (2000/01 onward), plus full closing odds from 2019/20**
- Handle the three verified traps: a missing season file returns HTTP 300 not 404, new `HxG`/`AxG` columns shifted positions in 2026/27 so parse by name, and English cards exclude the first yellow of a second-yellow red
- Canonical schema, `known_at` on every row, identity crosswalk for teams
- Snapshot mechanism
- Walk-forward harness with metrics, calibration and the leakage canary test
- Two baselines (league average, shrunken rate) evaluated at match level, **against a real market baseline from the closing odds**

**Exit test**: a report showing baselines scored on multiple seasons and compared against the closing-odds market baseline, with the canary test failing any leaking model. If the harness cannot demonstrate that a deliberately leaking model gets caught, the milestone is not done.

## M2 — Player-level data

**Gate before starting: verify API-Football's free tier serves the seasons we need.** If it does not, this milestone needs a different plan and the project may be limited to match-level markets.

- API-Football adapter: fixtures, results, per-player match stats (fouls committed and drawn, tackles, cards, duels)
- Budget the 100 requests/day cap: roughly 25/week live, and around 380 per season of backfill, so historical loading runs as a slow background activity over days
- Lineup polling in the 20 to 40 minute pre-kickoff window, which is later than originally assumed
- Player identity crosswalk with the halt-on-unresolved rule
- Referee appointment ingestion
- Raw response cache, replayable parsing
- Freshness checks and alerting

**No FBref adapter.** It is blocked behind a Cloudflare interactive challenge and its advanced data was deleted in January 2026, which removes the opponent take-on features it was wanted for. See [02-data-sources.md](02-data-sources.md).

**Exit test**: a full season of player-match rows reconstructed from scratch offline from the raw cache, with zero unresolved identities.

## M3 — The fouls model

- Feature builders, all `as_of` aware
- Expected minutes model
- Model ladder for `player_fouls_committed`: shrunken rate, negative binomial GLM, LightGBM Poisson
- Full backtest, calibration analysis, champion selection

**Exit test**: the champion beats the shrunken-rate baseline on walk-forward log loss by more than its confidence interval. If it does not, the baseline is the champion and that is a legitimate outcome.

## M4 — Publication and review

- Prediction publication to Postgres, pre-lineup and post-lineup
- Matchday lineup poller
- Grading and weekly review job
- Telegram alerting
- All GitHub Actions schedules live

**Exit test**: one full matchweek predicted, published, lineup-updated, settled, graded and reviewed without manual intervention.

## M5 — The site

- Next.js shell, Supabase client, RLS verified
- Fixtures, match detail with the interactive line explorer, track record, model arena, weekly review, methodology
- Supabase Auth with magic links
- Matchday realtime updates
- Responsible gambling compliance

**Exit test**: someone who is not Oliver can find a prediction, understand what it means and check whether past ones were right.

## M6 — Cards and tackles

- `player_cards` as a binary market, `player_tackles` as a count market
- Reuse the entire harness and site with no structural changes

**Exit test**: adding these required a market definition, feature additions and model registration, and no changes to backtest or site plumbing. If it required more, the abstraction failed and gets fixed here.

## M7 — Odds and value, heavily reduced in scope

Research killed most of what this milestone was going to be. There is no free source of player fouls odds. See [ADR-009](decisions/ADR-009-fair-odds-only.md).

- Manual odds entry admin page for the specific lines being tracked. This is the main deliverable, not a fallback
- Value calculation with margin removal, and closing line value tracking on that small sample
- Optionally, `player_to_receive_card` from The Odds API as a weak comparator for the cards market, noting it comes from US bookmakers rather than UK ones

**Exit test**: closing line value measurable on a real, honestly labelled sample. A small sample is the expected outcome, and the reporting must say so rather than dress it up.

## M8 — Season operations

- Season rollover with no hard-coded team lists or years
- Weekly retraining
- A full season of unattended running

## Later, deliberately unscheduled

- Charging for access. Not until the track record justifies it. Requires a hosting move off Vercel Hobby and a payment rail that permits sports forecasting.
- Additional markets (shots, offsides).
- Additional leagues.
- Public API.

## What would make us stop

Worth writing down while it is easy to be honest:

- The model cannot beat baselines after a genuine attempt. Then the answer is that the market prices these well and the interesting product was the transparency, not the edge.
- Free data sources close off to the point where the pipeline cannot run at zero cost.
- The weekly review stops happening for a month, which means the project is not actually being run.
