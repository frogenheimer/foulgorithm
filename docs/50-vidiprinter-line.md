# The vidiprinter as one line

**Status: Decided 2026-08-30.** Oliver's brief: tidy the vidiprinter into a
single row with slightly larger text, run through the successful events
first with each one animating in and out, and put the full report behind a
dropdown on that row.

> 💡 **One verdict at a time.** The homepage printer stops being a scrolling
> box of eighteen lines and becomes one line that changes: the bets that
> landed, newest game first, then the ones that did not, each sliding in,
> holding, and sliding out. A disclosure on the same row opens the whole
> feed for anyone who wants to read it.

---

## 🎯 What it does

- **One row.** Mono, uppercase as before, one step larger (`--t-sm`), a
  left-hand kicker (`VIDIPRINTER`) and the current line beside it. The row
  keeps its height between lines so the page never jumps.
- **Successes first.** `vidiprinterLines` still builds every settled bet,
  newest game first. The component plays every `won` line before any
  `lost` line, then loops. Nothing is dropped: a reader who waits sees the
  misses too, and the full report holds everything.
- **In and out.** Each line slides up into the row, holds for about four
  seconds, and slides out the top as the next one comes in. Reduced motion
  gets the same line every four seconds without the slide. The animation is
  CSS, one keyframe pair, no scroll physics.
- **Full report.** A `<details>` disclosure at the right end of the row
  (`Full report · 46`) opens the complete feed beneath it, in the same
  order the ticker plays. Closed by default. The count is the number of
  settled bets on the feed.
- **The sample goes.** The `TEMPORARY` block on the homepage and the sample
  lines are deleted: five games have settled and the feed is real.

---

## 🛑 Not changed

- The line format (`TOT v NEW · PAX · SAFE · CAME IN`) and its two tones.
- Where it sits on the homepage.
- `lib/vidiprinter.ts`'s verdict rules; only its cap is lifted so the
  report is complete.

---

## 🧱 Build

- `components/home/Vidiprinter.tsx` rewritten: ordered lines, an index on a
  timer, one visible line with enter and leave classes, the disclosure.
- `vidiprinter.module.css`: the row, the kicker, the keyframes, the report.
- `lib/vidiprinter.ts`: `orderForTicker(lines)` (won first, stable), cap
  removed by default.
- `app/page.tsx`: sample block and `SAMPLE_PRINTER` removed.
- Tests: `lib/vidiprinter.test.ts` for the ordering and the count.
