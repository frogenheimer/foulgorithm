# The display audit: one set of picks, shown three ways

**Status: Written 2026-08-24, changes shipped the same evening. Partly
revised the same day: Oliver ratified each change individually, and two came
out differently. [37-display-decisions.md](37-display-decisions.md) is the
record of what stands.** Oliver asked for a critical audit of how the site
displays information, with simplification as the goal. This is the audit,
what changed on the back of it, and what is deliberately left for later.

---

## 🎯 The diagnosis

The site had grown **two parallel pick systems** and displayed both, which is
the root of most of the clutter:

1. **The odds-tier ladder** (`_slip_at_odds`): each character builds
   combinations to 2/1, 3/1, 5/1, 10/1, 20/1. Born as the equal-risk
   comparison, it filled the fixture page with a five-by-five grid of prices
   that nothing scores and nothing settles as a unit.
2. **The committed slates** (`build_slates`): the same three fixed shapes for
   all five, versioned, binding at first kickoff, scored by the league table.
   These are the picks that actually count, and until tonight the site barely
   showed them.

When the picks that count are hidden and the picks that do not count fill a
page, the display logic is upside down. Everything below follows from turning
it right side up.

## ✅ What changed tonight

- **The league table never disappears.** Zeros are a state, not an absence:
  the table renders at 0-0-0 with a one-line note until the first round
  settles. It vanishing read as a bug, and was reported as one.
- **The fixture page leads with the five's committed picks**, as a matrix:
  players down, characters across, a filled cell is a pick at its line in the
  character's colour, and the players they agree on rise to the top. The
  odds-tier ladder is gone from the page, including its embedded copy under
  the interactive pitch.
- **The stats sheet lives on the fixture page**, pinned to that game, and the
  standalone stats page and its nav entry are retired. A picker for a game
  you are already on is furniture; the facts belong next to the picks they
  contextualise.
- **The homepage cards show the crossover** (shipped earlier this evening):
  the legs the five most agree on, backed-by counts, house-blend pricing, no
  single temperament. Cards and picks built before the team sheets carry an
  asterisk and regenerate at T-60.
- **The five page shows every committed slate in full**, one disclosure per
  character, legs grouped by game, with the binding rule stated.

## 🗃️ Where the record actually lives, because Oliver asked

Every pick surface is backed by an append-only store, all committed to git,
which makes the history tamper-evident:

| what | where | versioning | which version counts |
|---|---|---|---|
| Every claim every model makes | `data/predictions/*.jsonl` | append-only, deduped by natural key, `lineup_confirmed` flagged | all of them; graded individually |
| The committed slates, 3 shapes x 5 models | `data/slates/*.jsonl` | versions append, never mutate | latest published before the round's FIRST kickoff |
| What each fixture card said | `data/picks/*.json` | versions append per fixture | last version before that fixture's kickoff |
| Outcomes | `data/graded/*.jsonl` | append-only | n/a |

So the "last pick" question is answered structurally: iterate the algorithm
mid-week as much as we like, every iteration is recorded, and the scoring
rules pick the binding version by timestamp, not by trust. Nothing needed
building; it needed saying in one place.

## ⚠️ Deliberately left for later

- **The crossover cards still derive from the tier ladders**, not the slates:
  two pick engines feed one site. The clean end state is one source, the
  slates, feeding the cards, the matrix and the table alike. Not churned
  tonight because the ladder also powers the pitch's swap-and-rebuild, which
  needs its own rethink now the ladder display is gone.
- **`fixtureSlips` still ships in the payload** for the same reason. It goes
  when the pitch rebuild is redesigned.
- **The teams and referees pages** were not audited tonight and deserve the
  same question: what here would a reader act on, and what is furniture.
