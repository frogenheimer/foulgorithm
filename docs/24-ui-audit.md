# UI audit, and why the UI kept not getting fixed

**Status: Audit, 2026-08-23. Nothing here is built yet.**

Commissioned because the same request had been made repeatedly and repeatedly
not delivered. The first section is about that, because the mechanism matters
more than the findings.

---

## 🎯 Why this kept happening

Four reasons, in order of how much each one mattered.

**1. Model work is scoreable and UI work is not.** A dispersion change either
moves log loss or it does not, and the answer arrives in ten minutes. A layout
change has no number attached, so when the two compete for attention the one
with a scoreboard wins every time. That is a bias in how work gets chosen, not a
judgement that layout matters less, and it explains why "site work first" was
agreed and then quietly not done across several sessions.

**2. Every page was built as a local problem.** Nine pages produced twenty-two
CSS modules and 566 class rules. The table on the stats sheet, the table on the
players page, the table on the referees page and the six others are nine
separate definitions of the same object. Nothing was reused because nothing was
built to be reused, and each new page made the next one cheaper to hand-roll
than to fit into a system that did not exist.

**3. The styleguide describes and does not constrain.** `ui-styleguide.md` says
"never hard-code a pixel radius or a spacing value". There are 56 hard-coded
font sizes and 31 hard-coded spacing values in the repo. A rule that is written
down and never checked is a preference, and preferences lose to whatever is
quickest at 2am.

**4. I never read the design system that already exists.** Two mature
styleguides sit in the other repos, one of them 175KB and battle-tested across a
production dashboard. They were not consulted before building any of this.

---

## 🧱 What the ENVRT guides do that this one does not

Taking the **method**, not the identity. Foulgorithm stays visually separate:
different palette, different type, no shared components, no brand marks. What
transfers is how the rules are shaped.

| ENVRT does | Foulgorithm does | Why it matters |
|---|---|---|
| **Closed scales.** "The dashboard uses 6 sizes. Anything else is an escapee." | Defines 6 tokens, then uses 10 raw px values | A closed set can be checked. An open one cannot |
| **Mandatory primitives.** "No raw `<input>`, `<select>`, `<button>`" | 7 shared components, used by 4 of 9 pages | Reuse has to be the cheap path or it does not happen |
| **A component index** listing what exists and where | None | You cannot reuse what you cannot find |
| **`npm run audit`,** ~36 rules, run in CI, with a ratchet baseline that only falls | Nothing | "Writing a rule here does not enforce it. Two scripts do that." |
| **One-family rules.** One grey, one green | Two stray hex values, one undefined token | Removes a decision per use |
| **Named surface layers** L0 to L3 | Three surface tokens, applied ad hoc | Depth becomes a decision instead of a lookup |
| **A named brand fingerprint** (`SectionCorners`) | None identified | Without one, "clean" converges on generic |

The last row is the one worth dwelling on. The ENVRT guide names the thing that
stops its design reading as default Tailwind. This site has no such element, and
its visual identity currently amounts to a green accent and a dot grid.

---

## 📊 Current state, measured

| Metric | Count | Comment |
|---|---|---|
| Pages | 9 | |
| Nav destinations | 8 | For a site whose content is one round of fixtures |
| CSS modules | 22 | |
| Class rules | 566 | ~63 per page |
| Shared UI primitives | 7 | `Card`, `SectionHead`, `StatTile`, `TileGrid`, `Badge`, `Note`, `Callout` |
| Pages using them | 4 of 9 | The five that do not are the five built most recently |
| Separate `.table` definitions | 8 | One object, eight implementations |
| Separate scroll containers | 8 | Same |
| Uppercase micro-label rules | 39 | Should be one |
| `tabular-nums` declarations | 44 | Should be one utility |
| Card shells (border + radius + surface) | 13 | Should be one |
| Hard-coded `font-size: Npx` | 56, across 10 values | Tokens exist and are bypassed |
| Hard-coded px spacing | 31 | Same |
| Hard-coded hex | 2 | `#fff`, `#b4442e` (the second is an undefined `--warn` fallback) |

**The type scale is the clearest single failure.** `--text-xs` through
`--text-hero` are defined in `globals.css`. Alongside them the repo uses 9, 10,
12, 13, 14, 15, 16, 17, 18 and 20px directly. Six tokens, ten raw values, no
relationship between them.

---

## 🗺️ Information architecture, as it actually stands

Every page and what it currently shows.

### `/` Home
1. Hero: what the site is, plus three route cards
2. **Most likely to commit a foul** — top 8 players, ranked
3. **Where the models disagree** — dot chart per fixture
4. League leaders rail — this season's foul leaders
5. **Five readings of the same evidence** — five character cards with tiered slips
6. **Every player, every fixture** — the fixture grid
7. "How we worked this out" — a long disclosure block

### `/stats` The stats sheet
Fixture picker · mirrored team comparison (8 metrics, hit dots) · referee panel ·
per-club player tables (concedes / wins) · caveats

### `/players` Every player, every market
Market tabs · per-game character shouts · filter bar · 250-row table · expandable
distribution per row

### `/referees`
Three stat tiles · sortable referee table with this round's appointments

### `/record` Track record
Three stat tiles · per-model table · reliability curve · column glossary

### `/characters` The five
Five character cards · disagreement chart · "no track record yet"

### `/characters/[id]`
Portrait and philosophy · this round's picks · settings table

### `/history`
Four stat tiles · season trend · foul distribution · referee chart · team table

### `/methodology`
Six prose cards

### ⚠️ The overlaps

Six of the nine pages show something another page already shows.

| Duplicated content | Appears on |
|---|---|
| Top foulers this round | `/` §2 **and** `/players` |
| Model disagreement chart | `/` §3 **and** `/characters` |
| Character picks | `/` §5 **and** `/characters` **and** `/characters/[id]` |
| Fixture-by-fixture player tables | `/` §6 **and** `/stats` **and** `/players` |
| Referee foul rates | `/history` **and** `/referees` |
| League foul leaders | `/` rail **and** `/history` |

The home page is the worst of it: five sections, four of which are now thinner
versions of a dedicated page built later. It reads as an accumulation rather
than a decision, because that is what it is.

**Nav is eight destinations** for a site whose entire subject is one round of
fixtures. Three of them (`/history`, `/methodology`, `/characters`) are
reference material a first-time reader does not need and a returning one visits
once.

---

## ✅ What to do about it

Ordered by leverage, not by effort.

### 1. Close the type and spacing scales, then enforce them

Six sizes, no exceptions, every raw px snapped to the nearest. Same for spacing.
This is mechanical and removes a decision from every future component.

### 2. Write `scripts/audit-ui.sh` and run it in CI

The single highest-leverage item, and the reason the ENVRT guide holds while
this one drifts. Rules to start with, each already violated:

- No raw `font-size: Npx` outside `globals.css`
- No raw px in `padding`, `margin`, `gap`
- No hex outside `globals.css`
- No new `.module.css` defining `.table`, a scroll container, or a card shell
- Every `overflow-x: auto` box carries `min-width: 0`

With the ratchet baseline: current counts are the allowance, going above fails,
nothing raises it automatically.

### 3. Build the primitives the pages keep re-implementing

`DataTable` (sortable, numeric-aware, scroll-safe), `Metric`, `MicroLabel`,
`Scroller`, `PageHeader`. Then migrate the four pages that use none of them.
Eight table definitions become one.

### 4. Collapse the information architecture

Proposed: **This round** (fixtures, stats, players in one surface) ·
**The five** · **Track record** · **Methodology**. Four destinations. The home
page becomes an entry point rather than a fifth copy of everything.

### 5. Decide on a fingerprint

One repeated structural device that makes a page identifiably this site. The
hit dots are the strongest candidate already in the repo: they are distinctive,
they carry meaning, and they appear nowhere else in this genre. Currently they
live on one page.

### 6. Then, and only then, visual polish

Density, rhythm, motion. Doing this first is what produced the current state:
nine locally-tidy pages that do not look like one product.

---

## ⚠️ What this audit does not cover

Accessibility beyond contrast and colour-independence, which have been checked.
No keyboard-navigation audit, no screen-reader pass, no focus-order review. The
expandable rows and the filter bar are the likeliest problems.
