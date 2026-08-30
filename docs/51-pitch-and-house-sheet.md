# The pitch at every width, one set of controls, and the house sheet as a dropdown

**Status: Decided 2026-08-30.** Oliver's review of the fixture page after
the 29 August games: players render off the pitch at half a monitor's
width, the toggles and labels above the pitch are confusing, the old house
panel reappears after a swap when the page is meant to show slips, and the
receipt and boarding-pass papers are to go. He likes the house panel itself
and wants it on every fixture page, folded under the bookie's slips.

> 💡 **Three changes to one page.** The pitch sizes itself to its own width
> instead of the viewport. The controls shrink to one toggle. The house's
> full sheet, every shout by line, lives in a disclosure under the three
> slips on every fixture page, played or not.

---

## 🎯 The pitch off its touchlines

**Why it happens.** The squad row is `bench | pitch | bench`, the benches
128px to 160px each. At a 1000px viewport the pitch gets about 640px, each
half 320px, and a 3-4-2-1 puts four line columns in that half: 80px a
column. A name may run to 14 characters and is not allowed to break inside
a word (docs: "Grave nberch" was worse), so "Verbruggen" and "Martinez" sit
wider than their column and overhang the touchline. Nothing clips them,
deliberately, because clipping hid the open dropdown.

**What changes.**

- **The pitch measures itself.** `.pitch` becomes a size container
  (`container-type: inline-size`). Marker size, name size and the rate
  scale with the pitch's own width between the phone and desktop sizes, so
  at 640px the names are a step smaller and eleven fit between the boxes.
  The viewport never decides a size on the pitch again.
- **Benches drop below the pitch between 760px and 1100px.** The squad row
  becomes one column, the pitch takes the full width, and the two benches
  sit side by side under it. Above 1100px the three-column row returns;
  under 760px the existing one-team map is unchanged.
- **The pitch's height follows its shape.** The 420px floor goes at the
  stacked widths; the 105:68 aspect ratio is enough once the pitch has the
  full width.

---

## 🎯 One toggle, two figures

- **Keep** the market toggle (fouls committed, fouls won, involvements),
  right-aligned on the pitch head row, on the same line as the formations.
- **Remove** the basis toggle (expected this match, career per 90) and the
  sentence under it. Each marker prints both figures the way the match
  table does: `0.92 / 1.10`, real per 90 then expected this match, mono, the
  expected figure in the stronger ink. The key line says so once: "Each
  marker is real per 90, then what the model expects here."
- **Keep** the key (home and away, out of position, changed by you) as it
  is: three channels on a marker need a key.
- Cup pages have no "expected", so the marker shows the one figure it has.

---

## 🎯 The house sheet as a dropdown

- **Under the slips, every fixture page.** A `<details>` block titled
  "Every shout by line" sits directly below the three bookie's slips. Open,
  it renders the existing `HouseSheet` panel: fouls committed and fouls won
  as two columns, 1+, 2+ and 3+ groups, the three tier badges. Closed by
  default.
- **Live like the slips.** After a swap on the pitch the disclosure's sheet
  is the recomputed one and its kicker reads "The house · your eleven", the
  same as the slips' heading. Reset the pitch and it goes back to the
  published sheet.
- **The regression goes.** The panel stopped rendering on its own once the
  slips arrived, except that a swap brought it back as a second, unasked
  block at the top. The sheet is now rendered in exactly one place, inside
  the disclosure, whether or not a reader has swapped.
- **The data is already there.** The board carries `houseSheet` beside
  `houseSlips`, and the archive slices carry both, so no pipeline change.

---

## 🛑 The papers

The receipt and boarding-pass variants of the house slips go, along with
the style toggle and its stored preference. The bookie's slip is the one
paper. `PaperSlip` keeps the `variant` prop for now (the SlipCard tests
cover it) but nothing on the site selects the other two; they are removed
outright in a follow-up once the card tests are trimmed.

---

## 🧱 Build

- `components/fixture/Pitch.tsx` and `pitch.module.css`: the container,
  the stacked mid-width layout, the two-figure marker, the head-row toggle,
  the basis toggle and note removed.
- `components/fixture/FixtureLive.tsx`: renders the slips, then the
  disclosure with the sheet (published or recomputed); receives both
  `houseSheet` and `houseSlips` from the page.
- `app/fixture/[slug]/page.tsx`: passes the sheet as well as the slips.
- `components/fixture/HouseSlips.tsx`: toggle and storage removed.
- Gates: `scripts/audit-ui.sh`, `scripts/check-mobile.sh 390` and `320`,
  `next build`, `make js-test`.
