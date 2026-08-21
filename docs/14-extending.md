# Extending the system

**Status: Decided**

The whole architecture exists to make additions cheap. This doc is the practical test of whether it worked: if any recipe below needs changes outside the files it names, the abstraction has failed and the abstraction gets fixed rather than worked around.

## The rule

**Every extension point is a registry or a declaration, never an edit to shared logic.**

Shared logic (the backtest harness, the store, the publisher, the site's data contract) must not contain a list of markets, a list of models, a list of sources or a list of leagues. If it does, adding one means editing it, and editing shared logic to add a thing is how a codebase stops being extensible.

A quick smell test: search for a market key, a model id or a league name outside its own module. Any hit is a bug.

## Add a market

Fouls, cards and tackles ship first. Shots, offsides, corners conceded and anything else follow this recipe.

1. Confirm the stat exists in `player_match_stats` for the history we hold.
2. Add a `MarketSpec` in `markets/`. Declare its distribution family, its line grid, its settlement note and its minutes threshold.
3. Check the empirical variance-to-mean ratio to confirm the family is right.
4. Run the existing baselines through the harness for the new market.

**Nothing else changes.** No harness edit, no site edit, no schema change. Steps 1 to 4 need no new modelling code, and only after them do you decide whether a bespoke model is worth building.

## Add a data source

1. New adapter in `sources/` implementing `fetch`, `parse` and `known_at`.
2. Document the `known_at` rule in the docstring, erring later rather than earlier.
3. Add its identifiers to the crosswalk so nothing joins on names.
4. Add it to the freshness checks.

Fetch and parse stay separate so parsing replays from the raw cache offline. A new source never touches feature or model code, because it lands in the same canonical tables everything else reads.

## Add a model

1. New class in `models/` implementing `fit` and `predict`, decorated with `@register`.
2. Declare `id`, `version` and `market`.
3. Run the harness. It is scored against the champion automatically.

A new model **never overwrites an existing one**. Predictions are keyed by model id and version, so challengers run silently alongside the champion until one earns promotion. Rolling back is changing which id is flagged champion, not reverting code.

## Change an existing model

**Bump the version, never edit in place.** `shrunk_rate` 1.0.0 and 1.1.0 coexist, get scored side by side and stay independently attributable. This is what lets the track record survive model changes: a step change in results can be pinned to a specific version on a specific date.

## Add a league

The system is Premier League only as a product decision, not a technical limit.

1. Add a row to `seasons` with its competition.
2. Add the competition id to the source adapter's configuration.
3. Populate the crosswalk for its teams.

**No season, league or team name is ever hard-coded anywhere.** The 2025 version hard-coded one season across around 140 URLs and 20 club names, so it broke every August. A test asserts no competition or season literal appears outside configuration.

The real cost of a new league is data quality and review burden, not code.

## Add a site page

The site reads Postgres and holds no business logic. A new view is a new query plus a component. Probabilities, fair odds and grading all arrive precomputed, so a page can never disagree with the model.

## Add an alert or a scheduled job

New workflow in `.github/workflows/`, calling an existing CLI command. Keep the minute discipline in mind: one long job beats many short ones.

## What must stay stable

These are the seams everything else depends on, so changing them is a real decision that needs an ADR:

| Seam | Why it is load-bearing |
|---|---|
| `Distribution` interface | Every market, model, metric and site chart derives from it |
| `MarketSpec` shape | The harness and site are generic over it |
| `fetch` / `parse` / `known_at` adapter contract | Offline replay and leakage defence both depend on it |
| Canonical id scheme | All history is keyed on it |
| `predictions` table key | Champion and challenger coexistence depends on it |

Everything else should be cheap to change. If it is not, that is worth fixing before the next feature rather than after.
