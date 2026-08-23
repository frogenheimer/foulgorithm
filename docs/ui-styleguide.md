# UI styleguide

**Status: Superseded, 2026-08-23. Read [brandbook.md](brandbook.md) instead.**

> ⚠️ **This guide described tokens without constraining anything.** It said
> "never hard-code a hex, a pixel radius or a spacing value" and the repo went
> on to contain 65 hard-coded font sizes, 39 hard-coded spacings and 19
> hard-coded radii. Nine pages produced 22 CSS modules and eight separate
> implementations of one table.
>
> None of that was disagreement. Nothing checked. The replacement closes every
> scale and `scripts/audit-ui.sh` enforces it in CI against a baseline that only
> falls.

The site presents probabilities about a gambling market. That sets the tone: it should read like an instrument, not like a tipster. Sober, dense, precise. If a design choice makes a number feel more certain than it is, the choice is wrong.

## Principles

1. **The number is the hero.** Chrome recedes. No decorative imagery, no gradients behind data, no icons that do not carry meaning.
2. **Never show a probability without its uncertainty.** A bare number implies a precision we do not have.
3. **Losses are as visible as wins.** The track record is the product. Anything that hides a bad week is a bug.
4. **No hype.** No "lock", no "banker", no urgency, no countdowns to an offer. This is a house rule and a regulatory one.
5. **Colour never carries meaning alone.** Always paired with a label, a value or a shape.

## Tokens

Defined once in `site/app/globals.css` as custom properties. **Never hard-code a hex, a pixel radius or a spacing value in a component.** If you need a value that does not exist, add a token.

### Colour

Light and dark are both selected, not flipped. Dark values are declared under both `@media (prefers-color-scheme: dark)` and `:root[data-theme="dark"]` so a future theme toggle wins in both directions.

| Role | Token | Use |
|---|---|---|
| Page plane | `--plane` | The page background |
| Surface | `--surface-1` | Cards, panels |
| Surface raised | `--surface-2` | Nested panels, hover states |
| Primary ink | `--text-primary` | Headings, values |
| Secondary ink | `--text-secondary` | Body copy |
| Muted ink | `--text-muted` | Axis labels, captions, hints |
| Border | `--border` | Hairline rings |
| Grid | `--grid` | Chart gridlines |
| Series 1 | `--series-1` | First categorical slot, blue |
| Series 2 | `--series-2` | Second categorical slot, orange |
| Sequential | `--seq-100` … `--seq-600` | Magnitude ramps, one hue |

The categorical palette is validated for colour-vision deficiency in both modes. **Do not add a series colour without re-running the validator.** Order is fixed and never cycled.

### Spacing

A 4px base scale: `--space-1` (4px) through `--space-10` (64px). Layout uses these only. Optical adjustments inside a component may use raw pixels, and should be rare enough to notice.

### Type

One family, the system sans. No display face, no serif.

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 11.5px | Table headers, axis ticks |
| `--text-sm` | 12.5px | Captions, legends |
| `--text-base` | 15px | Body |
| `--text-lg` | 18px | Section headings |
| `--text-xl` | 22px | Page headings |
| `--text-hero` | 30px | Stat tile values |

Numbers that align vertically get `font-variant-numeric: tabular-nums`. Standalone large figures keep proportional figures.

### Radius and elevation

`--radius-sm` 6px, `--radius-md` 10px, `--radius-lg` 14px. Elevation is a hairline border, never a shadow. Shadows imply physicality this design does not want.

### Motion

`--ease` and `--duration-fast` (120ms) / `--duration-base` (200ms).

Motion clarifies state change and nothing else. Hover feedback, expand and collapse, and a single entrance fade. **No parallax, no scroll-jacking, no animated counters.** An animated number is a number you cannot read, and on a page about probability that is actively harmful.

All motion respects `prefers-reduced-motion`.

## Structure

```
site/
  app/
    layout.tsx          Shell, nav, footer
    page.tsx            This round's predictions. The product
    history/page.tsx    26 seasons of context
    methodology/page.tsx How it works, and where it is wrong
    globals.css         Tokens only, plus element resets
  components/
    ui/                 Primitives: Card, StatTile, Table, Badge, Nav
    charts/             One file per chart type
  lib/
    data.ts             Typed reads of the JSON the pipeline writes
    format.ts           Number and date formatting. One place
```

**Rules:**

- A component in `ui/` knows nothing about fouls. It is generic or it does not belong there.
- A component in `charts/` takes data and renders it. It never fetches.
- Formatting lives in `lib/format.ts`. A `toFixed` in a component is a bug, because it is how two places end up disagreeing about decimal places.
- Pages compose. They do not define layout primitives inline.

## Charts

Governed by the visualisation method already in use. The rules that bite most often here:

- **Never a second y-axis.** Two measures of different scale get indexed to a common base, or two charts.
- **Bars imply a zero baseline.** Values clustered far from zero get a dot plot instead.
- **A legend for two or more series**, none for one, since the title names it.
- **Hover is default**, not a nicety. Every chart has a hover layer with a bigger hit target than the mark.
- **A table view exists** for anything a chart shows, so the data is reachable without colour.

## Accessibility

- Contrast meets WCAG AA in both themes.
- Every chart has a text alternative and a keyboard path.
- Focus rings are visible and never removed.
- Semantic HTML first. A `div` with a click handler is a bug.
- Interactive targets at least 44px on touch.

## Responsible gambling furniture

Persistent in the footer on every page: 18+, the National Gambling Helpline, and a plain statement that this is not advice and nothing is guaranteed. Safer-gambling links live in **one config value**, not scattered through templates, because the charity landscape is shifting and a dead link should be a one-line fix.

See [13-legal-and-ethics.md](13-legal-and-ethics.md).

## Before you ship a UI change

- Tokens used, no raw hex or magic numbers.
- Light and dark both checked, by looking at them.
- Every probability shown with its uncertainty or its sample size.
- No language implying certainty.
- Rendered and eyeballed at 375px, 768px and 1280px.
- Wide content scrolls inside its own container. The page body never scrolls sideways.

---

## Visual reference, 2026-08-22

Reference: `slaten.domenicogriffo.com`. A product marketing site, so not everything
transfers, but the shell is right for a data product.

### What we take

**A narrow icon rail, not a top nav.** Roughly 64px, icons with labels on hover.
It frees the full width for content, which matters when the content is tables,
and it scales as sections are added without the horizontal-overflow problem the
top nav already hit once.

**Monospace for display type.** Unusual and correct here. A monospace headline
signals "instrument" rather than "publication", it sets our numbers and our
headings in the same voice, and it sidesteps the earlier problem where the
serif chosen for editorial weight had no tabular figures at all.

**One accent, used sparingly.** Their whole interface is neutral with a single
bright colour carrying every call to action. Ours is blue and should behave the
same: neutral surfaces, accent reserved for the thing that matters on each
screen.

**Dashboard card grid.** Distinct cards, generous internal padding, a hairline
border, no shadows. This maps directly onto the three-region home in
[19-page-structure.md](19-page-structure.md).

**Inline mini-charts inside cards.** Small bars sitting next to a number rather
than a chart section of their own. Our pack already has the pieces.

### What we do not take

**Their accent colour.** A chartreuse that sits near 1.8:1 on white. Fine for a
marketing button with a dark label, disqualifying for anything encoding data,
and it would fail the palette validator immediately.

**Avatars and photography.** They lean on faces throughout. We have no player
images and no licence for any, and identity comes from initials and club
accents instead.

**Marketing rhythm.** Alternating full-bleed persuasion sections suit a pricing
page. We are a tool: one shell, dense content, no scroll narrative.

### The rule that does not bend

Their layout is a template for *structure*, never for *claims*. Every number on
our version still carries its uncertainty, its sample size and its band word.
A prettier shell must not quietly turn an estimate into a promise.

## Checking narrow widths

**Do not judge mobile layout from a screenshot.** Headless Chrome will not open
a viewport narrower than 500px, so `--window-size=390` renders the page at 500
and then CLIPS the image to 390. Text appears cut off at the right edge and it
looks exactly like a page overflowing its viewport. It is not, and reading it
that way has twice cost a round of fixing layout that was already correct.

Run `scripts/check-mobile.sh [width]` instead. It loads each route inside an
iframe of the requested width, which gets a genuine viewport of that size, and
compares `scrollWidth` against it. Equal is correct. Wider is a real bug, and
the widest offending element is named.

```
route                      viewport  scrollWidth  verdict
/stats                          390          390  ok
/characters/alan                390          530  OVERFLOWS  table.characters_table@763
```

Both 390 and 320 should pass before any layout change ships.

### The rule, and the trap inside it

Wide content scrolls inside its own `overflow-x: auto` box. The page body never
scrolls sideways.

`min-width: 0` on that box is load-bearing and easy to leave out. A grid or flex
item defaults to `min-width: auto`, which refuses to shrink below its contents,
so a 622px table inside a scroller that is itself a grid item will still push
the whole page to 622px. The scroller looks correct and does nothing. The shared
`.scroll-x` helper in `globals.css` carries it; a bespoke one must too.
