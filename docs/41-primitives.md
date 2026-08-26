# Primitives: what already exists

**Status: Decided, 26 August 2026.**

Read this before writing a component, a table, a pitch, a card or a stat block.
It is a list of what is already built and where it lives.

> 🛑 **Do not rebuild a primitive. Extend it.** The cup pages grew a second
> pitch beside the fixture pages' one, and the copy lost the position badges,
> the out-of-position ring, the bench values and the key. That is what a copy
> always loses: not the obvious things, the ones that took a bug to learn.
> If a primitive nearly fits, add a prop. If it does not fit at all, say so out
> loud in the PR rather than forking it quietly.

---

## 🎯 The rule

Three questions, in order, before any new component:

1. **Is it in the table below?** Then use it.
2. **Is it nearly in the table?** Then add a prop to the existing one. A
   `readOnly` flag is cheaper than a second implementation, forever.
3. **Is it genuinely new?** Then build it, put it in `components/kit`, and add
   a row here.

A component that lives outside `components/kit` and is used by more than one
page is a primitive that has not been promoted yet.

---

## 🧱 The primitives

### Layout and chrome

| Primitive | Where | Use for |
|---|---|---|
| `PageHeader` | `components/kit` | Every page's title, kicker and lede |
| `SectionHead` | `components/kit` | An H2 with its explanation |
| `Card` | `components/kit` | Any panel. `flush` for a table body, `hero` for the page's one deep panel |
| `MicroLabel` | `components/kit` | The uppercase tracked label above a figure. There were 39 of these before it existed |
| `Callout` | `components/kit` | One thing the reader must know first |
| `Note` | `components/kit` | A quiet caveat under a block |
| `Prose` | `components/kit` | Running text |
| `Scroller` | `components/kit` | Anything that has to scroll sideways |

### Data

| Primitive | Where | Use for |
|---|---|---|
| `DataTable` | `components/kit` | **Every table.** Sorting via `sortKey`/`onSort` and a `sort` on each `Column`. Row expansion via `expanded`/`renderExpanded` |
| `Column<T>` | `components/kit` | A table column. `numeric` right-aligns and applies tabular figures |
| `Metric` / `MetricRow` | `components/kit` | A labelled figure, and a row of them |
| `Odds` | `components/kit` | A decimal price. `muted` when it is an estimate |
| `Dots` | `components/kit` | A small distribution |
| `Badge` | `components/kit` | A status pill |
| `Thin` / `thinRow` | `components/kit` | **The thin-evidence mark.** One explanation of what "thin" means, everywhere |
| `Estimated` | `components/kit` | Marks a number we inferred rather than observed |
| `Skeleton` | `components/kit` | Loading state |

### Controls

| Primitive | Where | Use for |
|---|---|---|
| `Toggle<T>` | `components/kit` | A segmented switch. Also the tab control on the cup pages |
| `Select<T>` | `components/kit` | A native select |
| `Combobox` | `components/kit` | A searchable picker |
| `Nav` | `components/kit` | The rail |

### Football

| Primitive | Where | Use for |
|---|---|---|
| **`Pitch`** | `components/fixture/Pitch.tsx` | **Both elevens on a pitch.** `readOnly` drops swapping and dragging; `bases` restricts which readings are offered. The cup pages use `readOnly` with `bases={["career"]}` |
| `ClubChip` | `components/kit/ClubChip` | A club badge. Falls back safely for a club we hold nothing for |
| `HouseSheet` | `components/fixture/HouseSheet.tsx` | The house's picks at the top of a fixture page |
| `Timeline` | `components/fixture/Timeline.tsx` | A match's events |
| `HeadToHead` | `components/HeadToHead.tsx` | Mirrored comparison rows, shared centre label |
| `CompetitionSwitcher` | `components/home` | League, League Cup, FA Cup |

### The helpers behind them

| Helper | Where | Why it exists |
|---|---|---|
| `who()` | `lib/who.ts` | **One identity per player.** Three sources spell a name three ways. Everything on a pitch keys off this and nothing keys off a display string |
| `lib/pitch.ts` | | Formation lines, occupancy, bench, shirt numbers, out-of-position |
| `lib/markets.ts` | | Market names and labels |
| `lib/clubs.ts` | | Kit colours and codes, with a safe fallback |
| `lib/format.ts` | | Number and date formatting |

---

## ⚠️ Where copies have already happened

Kept as a list because each one cost a rebuild.

- **The pitch.** `CupPitch.tsx` existed for about an hour. Deleted; the cup
  pages now pass `readOnly` to the real one.
- **Tables.** Nine pages produced eight implementations of one table before
  `DataTable`. `scripts/audit-ui.sh` rule B7 fails the build on a raw `<table>`
  and B9 on a standalone `.table` class.
- **The thin mark.** Rule B12 fails on a thin-evidence style defined outside
  `components/kit`. It fired within a day of being written.
- **Card shells.** Thirteen hand-built ones before `Card`.
- **Uppercase labels.** Thirty-nine before `MicroLabel`.

---

## ✅ Checklist before a new component

- [ ] Searched this page for it
- [ ] Searched `components/kit` for it
- [ ] Considered a prop on the nearest existing one
- [ ] If genuinely new: does it belong in `kit`?
- [ ] Added a row here if so
- [ ] `scripts/audit-ui.sh` passes without raising a baseline
