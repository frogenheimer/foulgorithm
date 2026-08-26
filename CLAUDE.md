# CLAUDE.md — Foulgorithm

Instructions for any Claude Code session working in this repository.

## This project has no connection to ENVRT

Read this section before anything else.

Foulgorithm is a personal project belonging to Oliver Woodcock. It is unrelated to ENVRT, the sustainability company, in every respect: separate GitHub account, separate hosting accounts, separate email, separate everything.

The global rules file at `~/.claude/CLAUDE.md` loads in every session on this machine and contains a large body of ENVRT-specific process. **Most of it does not apply here.**

**Rules that DO carry over** (personal preferences, not company process):

- No `Co-Authored-By` lines in commits, ever.
- Never `git push` without explicit approval.
- Prefer specific paths over `git add .`.
- **Work directly on `main`.** No feature branches for now, by Oliver's request, for simplicity. Keep `main` deployable, since it is what Vercel builds.
- Writing style: no em dashes, no oxford commas, active voice, plain English, specific over vague.
- Write tests before implementations. Run tests before committing.
- **Never rebuild something that already exists.** Read
  [docs/41-primitives.md](docs/41-primitives.md) before writing any component,
  table, pitch, card or stat block. If a primitive nearly fits, add a prop to
  it; do not fork it. The cup pages grew a second pitch beside the fixture
  pages' one and the copy silently lost the position badges, the
  out-of-position ring, the bench values and the key.
- Share SQL in chat so it can be applied by hand.

**Rules that DO NOT apply here:**

- The entire Notion workflow. Do not write to ENVRT Notion. Do not create Release Notes, Roadmap rows, Ideas & Requests entries, ADR database rows or Decision Log entries in Notion for this project. This project's decisions live in `docs/decisions/` as markdown.
- The ENVRT documentation emoji conventions and page templates.
- ENVRT marketing copy rules, regulatory context, DPP conventions and UI styleguides.
- The ENVRT memory directories. This project has its own.
- Anything referencing envrt-dashboard, envrt-site, envrt_lab or envrt-redirect.

If a rule from the global file seems to conflict with this file, this file wins inside this repository.

## Working style here

- **Keep chat replies very short and plain.** A few lines. No jargon, no walls of text.
- **Detail goes in the repo, not in chat.** Reasoning, trade-offs and context belong in `docs/` and `docs/decisions/`. Write it down there, then say the one-line version in chat.
- Oliver runs things from VSCode. Prefer a runnable file or a `make` target over a long shell incantation.
- Disagree by default. Stress-test ideas before agreeing with them.
- This is a side project. Bias to shipping something that works over designing something perfect.

## Non-negotiable engineering rules

These exist because the previous version of this project (`~/Documents/Foulgorithm`, 2025) failed on exactly these points.

1. **No look-ahead, ever.** Every fact carries a `known_at` timestamp. Features get built as of a timestamp. If you cannot prove a feature was knowable before kickoff, it does not go in the model. See [docs/07-backtesting.md](docs/07-backtesting.md).
2. **No silent failures.** Never write a bare `except:` that swallows an error into a default value. The old code turned every failure into "multiplier = 1" and nobody noticed for months. Fail loudly.
3. **No name-keyed joins across sources.** Team and player names differ between every data source. All joins go through the identity crosswalk. See [docs/04-identity-resolution.md](docs/04-identity-resolution.md).
4. **Models return distributions, not point estimates.** See [docs/06-modelling.md](docs/06-modelling.md).
5. **A new model never overwrites an old one.** Predictions are keyed by model id and version. Challengers run alongside the champion.
6. **£0.** Do not introduce a dependency, service or tier that costs money without flagging it first. See [docs/09-dev-workflow.md](docs/09-dev-workflow.md).
7. **Notebooks contain no logic.** They import from `foulgorithm` and display things. Anything worth keeping moves into the package with a test.
8. **Extensions are registrations, never edits to shared logic.** Shared code must contain no list of markets, models, sources, leagues or seasons. Adding one of those means adding a file, not editing the harness, the store, the publisher or the site. See [docs/14-extending.md](docs/14-extending.md).

## Where things live

| What | Where |
|---|---|
| Design decisions | `docs/decisions/` (markdown ADRs, numbered) |
| Architecture and methodology | `docs/` (numbered, see `docs/README.md`) |
| Open questions and known risks | `docs/12-risks-and-open-questions.md` |
| Ideas not committed to | `docs/ideas.md` |
| Modelling reasoning, append-only | `docs/modelling-log.md` |
| Roadmap | `docs/11-roadmap.md` |
| Database schema | `supabase/migrations/` |

## Before you commit

- Tests pass.
- No secrets in the diff. Keys live in `.env`, which is gitignored, and in GitHub Actions secrets.
- If the change alters methodology, data sources or schema, update the relevant doc in the same commit.
- If the change reflects a decision that future-you would otherwise reverse-engineer, write an ADR.
