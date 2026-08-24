.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt snapshot backtest ingest predict review site clean \
        check js-test site-build ui-audit data

# Everything runs with src/ importable, because the package is not reliably
# installed into the venv and every target needed the prefix by hand.
export PYTHONPATH := src
PY := .venv/bin/python
PIP := .venv/bin/pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create the virtualenv and install everything
	python3.11 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Done. Copy .env.example to .env and fill it in."

test: ## Run the test suite
	$(PY) -m pytest -q

lint: ## Check formatting and lint rules
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

fmt: ## Fix formatting
	$(PY) -m ruff format src tests
	$(PY) -m ruff check --fix src tests

snapshot: ## Freeze the current database to a parquet snapshot for experiments
	$(PY) -m foulgorithm.cli snapshot

backtest: ## Run walk-forward evaluation of all registered models
	$(PY) -m foulgorithm.cli backtest

ingest: ## Ingest one source. Usage: make ingest SOURCE=fbref [CACHED=1]
	$(PY) -m foulgorithm.cli ingest --source=$(SOURCE) $(if $(CACHED),--cached,)

review: ## Grade settled predictions and write the weekly review
	$(PY) -m foulgorithm.cli review

site: ## Run the Next.js dev server
	cd site && npm run dev

clean: ## Remove caches and build artifacts. Leaves data/raw alone.
	rm -rf .pytest_cache .ruff_cache **/__pycache__ site/.next

site-data: ## Regenerate the JSON the site reads
	$(PY) -m foulgorithm.publish.site_export

predict: ## Predict the next round of fixtures
	$(PY) -m foulgorithm.publish.predict_round

audit: ## Report exactly what data we hold and whether it is enough
	$(PY) -m foulgorithm.store.audit

characters: ## Publish every character's view of the upcoming round
	$(PY) -m foulgorithm.publish.character_round

gameweek: ## The whole round: refresh, settle, predict, verify, commit. DRY=1 rehearses, PUSH=1 pushes
	$(PY) -m foulgorithm.jobs.gameweek

# ---- offline study re-runs. Each prints its tables and needs no network and
# ---- no session. Rough runtimes on this machine are in the comment.

study-season-totals: ## C1 gate: how much of a stale year season totals recover (~10 min)
	$(PY) -u -m foulgorithm.backtest.season_total_study

study-team-context: ## C2 gate: archive against match-store context, both footings (~20 min)
	$(PY) -u -m foulgorithm.backtest.team_context_study

study-league-pool: ## C3 gate: six leagues on one scale, scored on England (~15 min)
	$(PY) -u -m foulgorithm.backtest.league_pool_study

study-dependence: ## Do players in a match move together? The reopen tripwire (~10 min)
	$(PY) -u -m foulgorithm.backtest.pairwise_dependence_study

study-provider-offset: ## The two providers compared player by player (~2 min)
	$(PY) -u -m foulgorithm.backtest.provider_offset_study

fit-calibration: ## Refit the published correction against the current model (~25 min)
	$(PY) -u -m foulgorithm.backtest.calibration_fit

players: ## Publish player predictions and character picks
	$(PY) -m foulgorithm.publish.player_round

serve: ## Serve the built static site locally (next start does not work with output: export)
	cd site && npm run build && cd out && python3 -m http.server 4319

player-backtest: ## Compare the five characters on player markets
	$(PY) -c "from foulgorithm.store.players import load_player_matches; from foulgorithm.backtest import player_harness as ph; h=load_player_matches(); [print(ph.report(ph.walk_forward(h,m,start='2024-01-01')),'\n') for m in ('player_fouls_committed','player_fouls_drawn')]"

season: ## Replay a season, gameweek by gameweek, five characters competing
	$(PY) -c "from foulgorithm.store.players import load_player_matches; from foulgorithm.backtest import season_competition as sc; print(sc.table(sc.run(load_player_matches())))"

record: ## Show what is in the append-only prediction store
	$(PY) -c "from foulgorithm.store import predictions as p; import collections; r=p.load_all(); print(f'{len(r)} claims on file'); print(dict(collections.Counter(x['model_id'] for x in r)))"

grade: ## Settle published predictions against results
	$(PY) -m foulgorithm.review.grade

# ---- one command, everything ----
#
# These were run one at a time and in the wrong order often enough to be worth
# a single target. A change is not finished until all four pass, so make it one
# thing to type and one thing to read.

js-test: ## Run the site's tests
	cd site && npx vitest run

site-build: ## Build the static site
	cd site && npm run build

ui-audit: ## Check the interface against the brandbook
	./scripts/audit-ui.sh

check: test js-test site-build ui-audit ## Everything: both suites, the build, the audit
	@echo
	@echo "All green."

data: ## Regenerate the site's data. The slow one, about 50 seconds.
	$(PY) -m foulgorithm.publish.player_round

api-football-probe: ## Say what the API-Football account actually gives us
	$(PY) -m foulgorithm.sources.api_football

leagues: ## Download the big-five player-match files
	$(PY) -m foulgorithm.sources.leagues

seasons: ## Fetch twenty seasons of league player totals
	$(PY) -m foulgorithm.sources.league_seasons

team-matches: ## Fetch twenty seasons of team match stats (~18 min)
	$(PY) -m foulgorithm.sources.team_match_stats

backfill-seasons: ## Add any newly listed stats to the season files already held
	$(PY) -m foulgorithm.sources.league_seasons --backfill
