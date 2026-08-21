# Data model

**Status: Proposed**

The schema exists to make one class of bug impossible: using information that did not exist yet. Everything else is secondary.

## The point-in-time principle

The 2025 version evaluated its own predictions using season averages computed from CSVs that already contained the matches being predicted. The reported win rate was meaningless. That failure was possible because the data had no concept of when a fact became knowable.

Every fact table therefore carries:

- `known_at` (timestamptz, not null): the earliest moment this row's content was knowable from public information.
- `source`: which adapter produced it.
- `ingested_at`: when we actually stored it, for debugging only. Never used in feature logic.

Feature builders take an `as_of` timestamp and filter `known_at <= as_of`. A test asserts that no feature function reads a row violating that. See [07-backtesting.md](07-backtesting.md).

Setting `known_at` honestly is a judgement call per source and it gets documented per adapter:

| Fact | `known_at` |
|---|---|
| Match result and player stats | Match kickoff plus 3 hours (when full time stats publish) |
| Fixture list entry | When the fixture was scheduled, approximated as season start |
| Referee appointment | The publication timestamp of the appointment, typically midweek |
| Official lineup | The timestamp we observed it, roughly 1 hour pre-kickoff |
| Odds snapshot | The moment of capture |

Where a source gives us history without telling us when each fact became public, we use a conservative rule and record that rule in the adapter docstring.

## Core tables

### Dimensions

**`teams`**
Canonical team identity. `id`, `name`, `short_name`, `founded`, plus nothing that changes often.

**`team_aliases`**
`team_id`, `source`, `source_key`, `alias`. The crosswalk. Every source name for a team resolves here.

**`players`**
Canonical player identity. `id`, `full_name`, `display_name`, `birth_date`, `primary_position`, `country`.

**`player_aliases`**
`player_id`, `source`, `source_key`, `alias`. Same pattern as teams and far more important, because player names vary wildly across sources.

**`referees`**
`id`, `name`, plus alias handling in `referee_aliases`.

**`seasons`**
`id`, `label` (for example `2026-27`), `competition`, `start_date`, `end_date`. No season is ever hard-coded in code. The 2025 version hard-coded 2024-25 in dozens of URLs and table ids, which broke annually.

### Facts

**`fixtures`**
`id`, `season_id`, `matchweek`, `kickoff_utc`, `home_team_id`, `away_team_id`, `venue`, `status`, `known_at`. Natural key for upserts is (`season_id`, `home_team_id`, `away_team_id`).

**`fixture_referees`**
`fixture_id`, `referee_id`, `role`, `known_at`. Separate from `fixtures` because appointments arrive later than fixtures and can change.

**`team_match_stats`**
One row per team per fixture. Fouls committed, fouls drawn, cards, tackles, possession, shots, and the rest. `known_at` set post-match.

**`player_match_stats`**
The spine of the whole project. One row per player per fixture: minutes, started, position played, fouls committed, fouls drawn, tackles, cards, take-ons attempted and completed, and so on. Around 57,000 rows for 5 seasons, which is small.

**`lineups`**
`fixture_id`, `player_id`, `status` (starting, bench, unused), `known_at`. Published roughly an hour before kickoff. The `known_at` here is genuinely important, because predictions made before and after lineup confirmation are different products and must be graded separately.

**`odds_snapshots`**
`fixture_id`, `market_key`, `entity_id`, `line`, `bookmaker`, `price`, `captured_at`, `is_closing`. Sparse by design. We will not have odds for most player markets most of the time and the schema must not assume otherwise.

### Model and output tables

**`model_runs`**
Every backtest or fit: `id`, `model_id`, `model_version`, `config_hash`, `git_sha`, `snapshot_id`, `market_key`, `started_at`, `metrics` (jsonb). This is the experiment log. It never gets deleted.

**`predictions`**
`id`, `fixture_id`, `market_key`, `entity_type`, `entity_id`, `model_id`, `model_version`, `distribution` (jsonb: the pmf), `predicted_at`, `lineup_confirmed` (bool), `is_champion` (bool).

Natural key is (`fixture_id`, `market_key`, `entity_id`, `model_id`, `model_version`, `lineup_confirmed`). A challenger model writing predictions never overwrites the champion's. The site filters on `is_champion` for its main views and shows challengers in the model arena.

**`outcomes`**
`fixture_id`, `market_key`, `entity_id`, `observed_value`, `settled_at`. Written by the review job from `player_match_stats`.

**`prediction_grades`**
Joins a prediction to its outcome with per-prediction scores: log loss at each line, Brier, CRPS, and simulated return where a price existed.

**`weekly_reviews`**
`id`, `period_start`, `period_end`, `summary` (jsonb), `notes` (markdown). One row per week, rendered on the site.

## Row level security

RLS on from the first migration, not retrofitted.

- Public read on `fixtures`, `teams`, `players`, `predictions` where `is_champion` and the fixture has kicked off or the prediction is free-tier, `prediction_grades`, `weekly_reviews`.
- No public write anywhere.
- Writes happen only with the service role key, which lives in GitHub Actions secrets and never in the site.

Access rules will tighten when a paywall arrives. Designing RLS now means that change is a policy edit rather than a rebuild.

## Migrations

Plain SQL files in `supabase/migrations/`, numbered and applied by hand in the Supabase SQL editor. Every migration gets pasted into chat when written so it can be applied without a migration runner. No ORM migrations, no automatic application.

## What we deliberately do not store

- Bookmaker odds beyond our own captured snapshots. We do not redistribute licensed data.
- Anything scraped from a source whose terms forbid storage, beyond the transient cache needed to parse it.
- Personal data of any kind beyond the account email Supabase Auth holds.
