# ADR-002 — Split Python compute from a JavaScript front end

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Python does all data work and modelling and writes results to Postgres. A Next.js application reads Postgres and serves the site. The two never call each other.

## Context

The project needs serious statistical tooling and a genuinely interactive website, on a budget of zero. Those pull in opposite directions: the statistics ecosystem is Python, and the free, fast, interactive web ecosystem is JavaScript.

## Options considered

**One Python web app** (FastAPI, Django or Streamlit). Simplest conceptually, one language, one deployment. Rejected because free always-on Python hosting is scarce and slow, free tiers cold-start badly, and the interactive charting we want is materially harder. Streamlit in particular would cap the site at "internal tool" quality, and the site is meant to be a product.

**One JavaScript stack**, doing the modelling in TypeScript. Rejected outright. The modelling libraries do not exist at the quality required, and Oliver's expertise is Python.

**Split with an API between them**, Python serving JSON to the front end. Rejected because it reintroduces the always-on Python hosting problem for no benefit. Postgres is already a perfectly good interface.

**Split with Postgres as the interface.** Chosen.

## Consequences

- Both halves sit on generous free tiers, because scheduled batch compute is free on GitHub Actions and static site serving is free on several hosts.
- The site is fast and cheap regardless of traffic, since it never triggers computation.
- Predictions are precomputed, which suits a pre-kickoff product and rules out anything genuinely live. Accepted, since in-play is an explicit non-goal.
- Two languages to maintain. Accepted, as the boundary is narrow and stable.
- The database schema becomes a contract between the halves, so schema changes need care on both sides.
