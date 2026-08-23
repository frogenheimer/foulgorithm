# Foulgorithm brandbook

**Status: Decided, 2026-08-23. This supersedes `ui-styleguide.md`, which described
tokens without constraining anything and was bypassed 56 times on font size alone.**

The site presents probabilities about a gambling market to people paying for the
privilege. That sets the tone: it should read like an instrument, not a tipster.
Light, dense, precise, boring on purpose. If a design choice makes a number feel
more certain than it is, the choice is wrong.

> 💡 **The scales here are closed.** Six type sizes, ten spacing steps, one
> accent. Anything outside them is an escapee and `scripts/audit-ui.sh` will say
> so. A rule nobody checks is a preference, and preferences lose at 2am.

---

## 🎯 The rule

Three sentences that decide most arguments.

1. **The number is the hero.** Chrome recedes. No decorative imagery, no
   gradients behind data, no icon that does not carry meaning.
2. **Never a probability without its uncertainty**, and never a price without
   what it would cost to take it.
3. **Losses are as visible as wins.** The track record is the product.

---

## 🎨 Colour

Light ground, white cards, one near-black rail, one accent. Categorical colour
is reserved for charts and never used as decoration.

### Ground and surface

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ground` | `#F6F6F4` | `#0E0F10` | The page behind everything |
| `--surface` | `#FFFFFF` | `#17191B` | Cards, panels, table bodies |
| `--surface-sunk` | `#F1F1EE` | `#101214` | Table headers, inset wells, inputs |
| `--rail` | `#16181A` | `#0A0B0C` | The navigation rail, in both themes |
| `--line` | `rgba(22,24,26,.10)` | `rgba(255,255,255,.10)` | Hairlines, card borders |
| `--line-strong` | `rgba(22,24,26,.20)` | `rgba(255,255,255,.20)` | Hover borders, dividers that matter |

The rail stays near-black in both themes. It is the one fixed element and it is
what makes a screenshot recognisable.

### Ink

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#16181A` | `#F7F7F5` | Headings, values, anything being read closely |
| `--ink-2` | `#4A4E52` | `#B9BDC0` | Body copy |
| `--ink-3` | `#71767A` | `#8B9094` | Captions, axis labels, micro-labels |

`--ink-3` on `--surface` measures 4.9:1. Nothing quieter than this carries meaning.

### Accent

**One.** `--accent: #1B7F4B` light, `#3FBF77` dark. Used for active state,
focus, the current selection and confirmed status. Never for emphasis, never on
a chart series, never two accents on one screen.

### Charts

Four categorical slots, fixed order, never cycled. Validated for deuteranopia
and protanopia.

| Token | Light | Dark |
|---|---|---|
| `--c1` | `#2563C9` blue | `#5B9BF5` |
| `--c2` | `#1B7F4B` green | `#3FBF77` |
| `--c3` | `#C77A0A` amber | `#E8A33D` |
| `--c4` | `#B23A34` red | `#E36A62` |

Sequential ramps use one hue: `--seq-1` through `--seq-4`, blue.

### Semantic

`--warn: #C77A0A`, `--bad: #B23A34`, `--good: --accent`. Colour never carries
meaning alone; every semantic use is paired with a word, a sign or a shape.

### Character colours

The five keep their own hues, and they are **data, not brand**: they identify a
series and appear nowhere else.

`--ch-alan: #2563C9` · `--ch-lily: #D2691E` · `--ch-valentina: #1B7F4B` ·
`--ch-tayler: #B8860B` · `--ch-bdog: #A8497F`

---

## 🔤 Type

One family. `Inter` with a system fallback, tabular figures on every number.
No display face, no serif, no monospace except in code blocks.

### Six sizes. Anything else is an escapee.

| Token | Size | Use |
|---|---|---|
| `--t-hero` | 30px | Stat tile values, the one number on a card |
| `--t-xl` | 22px | Page title, h1 |
| `--t-lg` | 17px | Section heading, card title |
| `--t-md` | 15px | Body, table cells |
| `--t-sm` | 13px | Captions, secondary table text |
| `--t-xs` | 11px | Micro-labels, axis ticks, badges |

Below 11px is never legible enough to carry meaning and is banned.

### Weight

400, 500, 600 only. No 700, no 300. A heading is distinguished by size and
colour, not by weight alone.

### Figures

`font-variant-numeric: tabular-nums` on **every** number that sits in a column,
handled by the `DataTable` and `Metric` primitives so no page has to remember.
Standalone hero numbers keep proportional figures.

---

## 📐 Space

A 4px base. Ten steps, `--s1` (4px) through `--s10` (64px). Layout uses these
only; a raw pixel inside a component should be rare enough to notice.

### Rhythm

| Between | Step |
|---|---|
| Label → value | `--s1` |
| Rows in a list | `--s2` |
| Elements in a card | `--s3` |
| Card padding | `--s5` |
| Cards in a grid | `--s4` |
| Sections on a page | `--s8` |
| Page title → first block | `--s7` |

### Widths

| Token | Value | Use |
|---|---|---|
| `--w-prose` | 68ch | Anything meant to be read as sentences |
| `--w-content` | 1240px | The default page column |
| `--w-wide` | 1560px | Dense grids only, where the extra width earns its place |

The rail is 64px, fixed, and becomes a scrolling top bar under 640px.

---

## 🧱 Elevation

Flat, with one exception. Cards get a hairline and the faintest lift; nothing
else gets a shadow.

| Layer | Recipe |
|---|---|
| **L0** page | `--ground` |
| **L1** card | `--surface`, `1px --line`, `--r-md`, `0 1px 2px rgba(22,24,26,.04)` |
| **L2** inset | `--surface-sunk`, no border, `--r-sm` |
| **L3** rail | `--rail`, no border |

Radii: `--r-sm` 6px, `--r-md` 10px, `--r-lg` 14px, `--r-pill` 999px.

---

## 🚦 Motion

One curve, `--ease: cubic-bezier(.2,0,.13,1)`. Two durations, `--d-fast` 120ms
for state and `--d-base` 200ms for anything that moves. Everything inside
`prefers-reduced-motion: reduce` collapses to zero.

Nothing animates on load. A number that fades in reads as less certain than one
that was already there.

---

## 🧩 Primitives

Mandatory. If a page hand-rolls one of these, the audit script flags it.

| Component | Replaces |
|---|---|
| `PageHeader` | every `h1` + lede pair |
| `SectionHead` | every `h2` + note pair |
| `Card` | the 13 hand-built card shells |
| `DataTable` | the 8 separate `.table` definitions |
| `Scroller` | the 8 hand-built `overflow-x` boxes, carries `min-width: 0` |
| `Metric` | stat tiles, hero numbers |
| `MicroLabel` | the 39 uppercase label rules |
| `Dots` | hit-rate runs. **The fingerprint** |
| `Odds` | any decimal price, with the margin note attached |

### The fingerprint

`Dots` is what makes a page identifiably this site: a run of filled and hollow
circles showing whether a line landed, most recent first. Filled against hollow
rather than two colours, so it survives greyscale. It appears on the stats
sheet, in player rows, in the track record and beside every combination leg.

---

## ✅ Checklist before any UI commit

- Every size from the six. Every space from the ten.
- No hex outside `tokens.css`.
- Any wide thing sits in a `Scroller`, which carries `min-width: 0`.
- Numbers in columns are tabular.
- Colour is never the only carrier of meaning.
- `scripts/audit-ui.sh` clean, `scripts/check-mobile.sh 390` clean.

---

## ⚠️ Why this exists

The previous guide said "never hard-code a pixel radius or a spacing value".
The repo contained 56 hard-coded font sizes across ten values and 31 hard-coded
spacings. Nine pages produced twenty-two CSS modules and 566 class rules, with
eight separate implementations of one table.

None of that happened through disagreement. It happened because nothing checked.
