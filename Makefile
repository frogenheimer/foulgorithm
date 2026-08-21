.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt snapshot backtest ingest predict review site clean

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

predict: ## Generate and publish predictions for upcoming fixtures
	$(PY) -m foulgorithm.cli predict

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
