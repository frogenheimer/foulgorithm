# Identity resolution

**Status: Decided and shipped, 2026-08-22.** (four crosswalks built, halt-on-unresolved enforced)

## Why this gets its own module

Multi-source sports data fails at the join. Every source spells things differently and the differences are not systematic:

| Source | Team | Player |
|---|---|---|
| FBref | `Nott'ham Forest` | `Gabriel Magalhães` |
| football-data.co.uk | `Nott'm Forest` | not applicable, match level only |
| API-Football | `Nottingham Forest` | `Gabriel dos Santos Magalhães` |
| Common usage | `Forest` | `Gabriel` |

The 2025 version keyed its CSV filenames on FBref display names and looked players up by exact string match. That works until a source changes a spelling, an accent gets normalised differently or a player is transferred, and then it silently produces wrong numbers rather than an error.

Fuzzy matching alone is not the answer either. Fuzzy matching is how you end up with Danny Ward the goalkeeper inheriting Danny Ward the striker's foul rate.

## The approach

Three layers, in order of preference.

### 1. Deterministic keys where a source provides them

FBref has stable player and squad ids in its URLs. API-Football has numeric ids. When a source gives a stable id, we store it in the alias table as `source_key` and never think about names again. This handles the large majority of records.

### 2. A committed crosswalk file

`data/reference/crosswalk_teams.yaml` and `data/reference/crosswalk_players.yaml` are checked into git. They map source keys and known aliases onto canonical ids. Teams are small and stable, so the team file is close to complete after one pass and gets a handful of edits each August when promoted clubs arrive.

The player file is bigger but only needs entries where deterministic ids are unavailable or disagree.

These files are data, not code, and they are reviewable in a diff.

### 3. Assisted matching for the remainder

For genuinely new records, a matching routine proposes candidates using normalised name similarity plus corroborating fields: birth date, club, position, nationality. A name match alone never resolves an identity. The routine writes proposals to `data/reference/crosswalk_pending.yaml` for a human to confirm, and confirmed entries move into the main crosswalk.

## The hard rule

**Unresolved identities halt the pipeline. They do not get skipped and they do not get guessed.**

If an ingestion run encounters a player or team it cannot resolve, it raises, writes the unresolved record to the pending file and stops that source's run. A test asserts every row in the current snapshot resolves.

This is deliberately annoying. Annoying is better than the alternative, where a transferred player quietly loses his history and the model prices him as a debutant.

## Normalisation helpers

Before comparison, names get normalised: unicode NFKD with accents stripped, lowercase, punctuation removed, common suffixes dropped (`FC`, `AFC`, `United` kept because it is discriminating), and known given-name orderings handled (`Son Heung-min` and `Heung-Min Son`).

Normalisation exists to generate candidates. It never confirms a match on its own.

## Transfers and loans

A player's canonical id is permanent. Club membership is a fact about a match appearance, not about the player, so it lives in `player_match_stats` and lineups rather than on the player record. A January transfer therefore needs no special handling: the history follows the player, and any club-level feature is computed from the club he played for in each match.

## Season rollover

Every August, three promoted clubs arrive and three relegated clubs leave. The rollover procedure:

1. Pull the new season's team list from the primary source by id.
2. Any team id not already in the crosswalk raises, so the human adds it deliberately.
3. Promoted clubs have Championship history we will not use for the top-flight model, so their team-level priors start from a league-average prior rather than from their second-tier numbers. That is a modelling decision, documented in [06-modelling.md](06-modelling.md), not an identity one.

No season or team list is ever hard-coded. The 2025 config file contained 20 hard-coded club names and around 140 hard-coded URLs, and would need manual editing every year to survive.
