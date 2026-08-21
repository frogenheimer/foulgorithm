# Decision records

One decision per file. Numbered sequentially, never renumbered.

An ADR is immutable once merged. To change a decision, write a new ADR that supersedes the old one, and edit the old one's status line to point at the replacement. Do not rewrite history: the value is in seeing what we believed at the time and why we changed our minds.

## Format

```
# ADR-NNN — Title

**Status**: Accepted | Superseded by ADR-NNN | Proposed
**Date**: YYYY-MM-DD

## Decision
One sentence. What we are doing.

## Context
What forced the decision.

## Options considered
What else was on the table and why it lost.

## Consequences
What this makes easy, what it makes hard, what we accept.
```

## Index

| ADR | Title | Status |
|---|---|---|
| [001](ADR-001-rebuild-not-extend.md) | Rebuild rather than extend the 2025 codebase | Accepted |
| [002](ADR-002-two-runtime-split.md) | Split Python compute from a JavaScript front end | Accepted |
| [003](ADR-003-point-in-time-data.md) | Every fact carries `known_at` | Accepted |
| [004](ADR-004-hosting-portability.md) | Host on Vercel Hobby, stay portable to Cloudflare | Accepted |
| [005](ADR-005-distributions-not-estimates.md) | Models return distributions, not point estimates | Accepted |
| [006](ADR-006-free-until-proven.md) | Free access until the track record justifies charging | Accepted |
| [007](ADR-007-identity-halts-pipeline.md) | Unresolved identities halt ingestion | Accepted |
| [008](ADR-008-two-supabase-projects.md) | Two Supabase projects for dev and prod | Accepted |
| [009](ADR-009-fair-odds-only.md) | Publish fair odds only, capture market prices manually | Accepted |
