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

**Two families, and the second is load-bearing.** Inter for the interface, a
monospace for figures.

| Family | Where | Why |
|---|---|---|
| **Inter** | Everything that is words | The default for modern dashboards for good reason: tall x-height, screen-designed, renders identically everywhere, ships every weight, and has tabular figures and a slashed zero as stylistic sets |
| **Geist Mono** | Odds, probabilities, hero figures, the dots ladder | A price is not prose. Monospace figures at a large size read as instrument output rather than as text, and every digit occupies the same column without being asked |

Fallback stacks are real: `Inter, ui-sans-serif, system-ui, sans-serif` and
`"Geist Mono", ui-monospace, "SF Mono", monospace`. Both are free and
self-hosted, so no third-party request and no layout shift.

Inter is loaded with `cv05` and `tnum` on, which gives a single-storey `a` and
tabular figures everywhere without asking a component to remember.

### Where the mono goes, precisely

Only three places. Mono everywhere is a terminal, which is the aesthetic this
deliberately moved away from.

- Any decimal price: `3.05`, `2/1`
- Any hero figure on a card: the one big number
- Micro-labels above figures, uppercase, tracked

Table cells stay Inter with tabular figures. They are read as rows, not as
readouts.

### Six sizes. Anything else is an escapee.

Six is the count Vercel's dashboard settled on and the count that survives
audit. More than six and nobody can tell two of them apart at a glance.

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

### Navigation

**240px, labelled, collapsible to 64px.** Not an icon-only rail.

The current 64px icon rail was defensible at four destinations and stopped being
so at eight: two of the icons are the same bar-chart glyph and nothing
distinguishes them without a hover. Every dashboard worth copying (Linear,
Stripe, Vercel, Grafana) runs a labelled sidebar around 240 to 256px, and the
reference this design is built from has labels too.

Collapsed state keeps the icons and is a user preference, not the default. Under
640px it becomes a scrolling top bar.

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

> 💡 **If it does not clarify, guide or confirm, it does not ship.** That is the
> whole test. Decoration on a page about probability reads as a distraction from
> the numbers, which is the opposite of what this product sells.

One curve, `--ease: cubic-bezier(.2,0,.13,1)`. Three durations.

| Token | Value | Use |
|---|---|---|
| `--d-fast` | 120ms | Hover, focus, active. State the user caused |
| `--d-base` | 220ms | Anything that moves or appears |
| `--d-slow` | 380ms | Panels, drawers, the fixture page opening |

Research puts the useful band at 200 to 400ms; below 150 an animation is not
perceived as motion and above 400 it delays the person. `--d-fast` sits under
that band on purpose: a hover state is feedback, not motion.

### Animate transform and opacity. Nothing else.

Both are GPU-composited and cost nothing. Animating `width`, `height`, `top` or
`left` forces layout on every frame and is the usual cause of a dashboard that
janks on a phone. A row expanding uses a transform, not a height transition.

### Where motion is allowed

- **State**: hover, focus ring, active tab. `--d-fast`.
- **Disclosure**: a row opening into its distribution, a fixture page arriving.
  `--d-base` to `--d-slow`, transform and opacity only.
- **Skeletons**: a shimmer in the shape of the content, never a spinner. A
  spinner says "wait"; a skeleton says "here is what is coming".

### Where it is banned

- **Numbers do not count up.** A figure that animates to its value reads as less
  certain than one that was simply there, and this site sells certainty about
  uncertainty.
- **Nothing animates on page load.** Content that fades in is content that was
  not ready.
- **Charts do not draw themselves.** The shape is the information; revealing it
  slowly withholds information for effect.

Everything inside `prefers-reduced-motion: reduce` collapses to zero duration,
not to a shorter one.

---

## 🧩 Primitives

Mandatory. If a page hand-rolls one of these, the audit script flags it.

| Component | Replaces |
|---|---|
| `Skeleton` | every loading state. Shaped like its content, never a spinner |
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

---

## 📚 What this was built from

Not invented. The decisions above track what dashboards people actually use all
day have settled on, with two deliberate departures.

| Decision | Source |
|---|---|
| Six type sizes, closed scale | Vercel's dashboard settled on six; more than that and two of them become indistinguishable |
| Inter for interface | The default for modern dashboards: screen-designed, tall x-height, tabular figures and a slashed zero as stylistic sets, renders identically everywhere |
| Mono for figures only | The common pairing for data products is a sans for interface and a mono for hero metrics. Mono everywhere is a terminal |
| 240px labelled sidebar | Linear, Stripe, Vercel and Grafana all run 240 to 256px with labels |
| 200 to 400ms motion band | Below 150ms is not perceived as motion; above 400ms delays the person |
| Transform and opacity only | Both GPU-composited. Animating width, height, top or left forces layout every frame and is the usual cause of a dashboard that janks on a phone |
| Skeletons, not spinners | A spinner says wait. A skeleton in the shape of the content says here is what is coming |
| Both themes from day one | Standard practice, not a later feature |

### The two departures

**Light by default.** Linear, Supabase and Vercel now design dark-first. This
does not, for two reasons. Dense numeric tables read better on light, which is
most of what this site is. And every betting site in this genre is dark, so
light is the cheaper differentiator. Dark ships alongside it, properly, not as
an inverted afterthought.

**No count-up numbers, no self-drawing charts.** Both are current fashion and
both are banned here. A figure that animates to its value reads as less certain
than one that was already there, and a chart that reveals itself withholds
information for effect. This site sells calibrated uncertainty; the visual
language should not undercut it.
