# Foulgorithm

A statistical model and public website for predicting player-level disciplinary and duel events in the English Premier League: fouls committed, cards and tackles.

The model publishes calibrated probability distributions and fair odds for every player in every fixture. It does not sell certainty. Every prediction we publish gets graded after the match and the full record stays public forever.

## Status

**Pre-alpha.** Foundations only. No data pipeline, no model, no site yet. See [docs/11-roadmap.md](docs/11-roadmap.md) for what happens next and in what order.

## What this is

| | |
|---|---|
| **Sport** | English Premier League |
| **Markets** | Player fouls committed, player cards, player tackles (see [docs/05-markets.md](docs/05-markets.md)) |
| **Output** | Full probability distribution per player per market, plus fair odds for every line |
| **Cost to run** | £0. Free tiers only, no card on file anywhere ([docs/09-dev-workflow.md](docs/09-dev-workflow.md)) |
| **Access** | Everything free while the model proves itself. Auth exists from day one so a paywall is a flag flip later |

## Read this before starting work

Two findings from source research on 21 August 2026 shape the whole project:

1. **API-Football is the only free source of current-season per-player fouls we can use** without a terms-of-service conflict. FBref is blocked and lost its advanced data in January 2026. FotMob objected to scraping. Understat has no fouls at all. There is no fallback.
2. **No free source of player fouls odds exists**, so we publish our own fair odds and make no systematic value claims.

Full detail and the verification log are in [docs/02-data-sources.md](docs/02-data-sources.md).

## Repository layout

```
docs/            Design docs and decision records. Read docs/README.md first
src/foulgorithm/ The Python package: ingestion, features, models, backtesting
tests/           Pytest suite. Tests get written before implementations
notebooks/       Exploration only. Notebooks call the package, never define logic
data/            Local working data. Almost entirely gitignored
supabase/        SQL migrations, applied by hand in the Supabase editor
site/            Next.js front end
scripts/         One-off operational scripts
.github/         Scheduled jobs
```

## Quickstart

Nothing runs yet. Once the pipeline lands:

```bash
make setup          # create venv, install deps, install pre-commit
make test           # run the test suite
make backtest       # walk-forward evaluation against local snapshot
make site           # next dev against the dev Supabase project
```

## Documentation

Start at [docs/README.md](docs/README.md). The docs are the source of truth for design decisions, not this file and not chat history.

## Responsible gambling

This project publishes statistical estimates for entertainment and research. It is not betting advice and it does not guarantee outcomes. 18+. Anyone in the UK who needs support can reach BeGambleAware on 0808 8020 133 or at begambleaware.org. See [docs/13-legal-and-ethics.md](docs/13-legal-and-ethics.md).
