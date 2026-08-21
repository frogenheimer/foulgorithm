# Reference data

The only directory under `data/` that is committed to git.

Everything here is a **decision**, not derived data. Crosswalk entries record how we resolved an identity, which is a judgement someone made and which must be reviewable in a diff and recoverable if a database is lost.

## Files

| File | Purpose |
|---|---|
| `crosswalk_teams.yaml` | Source keys and aliases mapped to canonical team ids |
| `crosswalk_players.yaml` | Same for players. Only needed where source ids are absent or disagree |
| `crosswalk_pending.yaml` | Unresolved identities awaiting human confirmation. Should normally be empty |
| `derbies.yaml` | Fixtures treated as high-stakes, maintained by hand |

## Working with the crosswalk

When ingestion halts on an unresolved identity (see [ADR-007](../../docs/decisions/ADR-007-identity-halts-pipeline.md)):

1. Look at the record written to `crosswalk_pending.yaml`.
2. Confirm the identity using corroborating fields, meaning birth date, club, position and nationality. A name match alone is never enough.
3. Move the entry into the appropriate crosswalk file.
4. Re-run ingestion.

Expect this a few times each transfer window and each August when promoted clubs arrive. It is a handful of lines of YAML and it is deliberately manual.

## Why derbies are a hand-maintained list

Inferring "big game" from head-to-head foul history is what the 2025 version did, using samples of 1 or 2 matches per season. That produced multipliers driven almost entirely by noise. A short list of genuine local and historic rivalries is more honest and more stable.
