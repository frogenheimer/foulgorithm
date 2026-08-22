# Design rebuild plan

**Status: Decided and shipped, 2026-08-22.** (built)

## Two blockers first

Neither is a design problem, and both would undermine any design built on top.

**1. Players with no history get zero expected minutes.** `expected_minutes`
returns 0.0 when a player has no prior appearances, so his expected fouls
collapse to nearly nothing. Promoted clubs are mostly such players, which is why
Hull currently shows **2.31** expected fouls against Manchester United's **10.2**.
That is not a modelling opinion, it is a hole. Minutes must fall back to a
positional and squad-role prior, exactly as rates already do.

**2. Team names do not join.** The foul history says "Brighton & Hove Albion",
the fixture list says "Brighton". Team-level comparison rows come back empty
because the join silently finds nothing. A fourth crosswalk, or better, one
canonical club table every source maps into.

Both are the same class of error the project was rebuilt to prevent: a lookup
that fails quietly and produces a plausible-looking number.

## What this site is for

**One question: who should I look at today, and at what price.**

Everything else is evidence for that answer, or proof we have been honest
before. Two audiences, one page:

- **The scanner** wants a shortlist and a reason. Thirty seconds.
- **The decider** wants the numbers laid out so they can form their own view,
  which is the pattern the tipster reference gets right.

The current build serves neither well: too sparse for the decider, too slow for
the scanner.

## The measured problem

At 1440px, one gameweek: **2,600px tall at roughly 5% ink coverage.** The page
is 95% empty. We over-corrected from 200 undifferentiated numbers into almost no
density, and sparse is not clear.

## Layout system

### Shell

Icon rail stays. Content becomes a **12-column grid** at a 1320px maximum,
rather than a 900px column floating in a 1440px viewport.

### Home

```
┌─────────────────────────────────────────────────────────────┐
│ CALENDAR STRIP        days with football, count per day     │  full
├──────────┬──────────────────────────────────┬───────────────┤
│ LEAGUE   │  DISAGREEMENT CHART              │  TODAY'S      │
│ LEADERS  │  the centrepiece                 │  SHORTLIST    │
│ 3 cols   │  6 cols                          │  3 cols       │
├──────────┴──────────────────────────────────┴───────────────┤
│ FIXTURE CARDS   2 or 3 per row, not stacked accordions      │  full
└─────────────────────────────────────────────────────────────┘
```

Ten fixtures then occupy roughly one screen instead of ten.

### Fixture page: the head-to-head table

The pattern from the tipster reference, done better. **Mirrored rows with a
shared centre label**, so comparison happens across one line rather than by
holding a number in your head while you find its opposite in a second table.

```
   Arsenal                                          Coventry
     11.4  ████████████▏      ▕███████        13.9
              Fouls committed per match
      2.1  ███████▏             ▕████████      2.6
              Yellow cards per match
```

A split bar between the two values does the comparison visually; the numbers
stay for anyone who wants them. Sections: **team form**, then **model output**,
then **players mirrored**, top five each side.

This is the "decide for yourself" surface, and it is where density is a virtue
rather than a failure.

## Visual system

### Light is the default

Dark suits the marketing references, where content is a few large statements.
Ours is dense numeric tables, and thin numerals on dark backgrounds bloom and
lose definition. Tune light first, keep dark as the alternate, follow the
system preference.

### Colour

| Role | Value | Rule |
|---|---|---|
| Accent | Slate green | Chrome only. Mark, active nav, price floors, focus |
| Data | Validated blue ramp | Everything encoding a value |
| Split bars | Blue against neutral | Never red against green, which is the worst possible pairing |

Green never encodes. It failed the data checks, and red-green deficiency
affects roughly 8% of men.

### Type

Monospace display stays. Body sans. **Tighter scale:** the current hero costs
300px to say one sentence.

### Space

Halve the vertical rhythm. Section gaps 64px to 40px, leaderboard rows 60px to
44px, hero 300px to 180px. Target roughly half the height for the same content.

### Texture

Drop the dot field in light mode, or take it to near-invisible. It currently
reads as competing texture, and it is decoration on a page where nothing else is.

## The centrepiece

**Where the five disagree.** Already computed, currently buried in a table.

One chart, all ten fixtures, five markers each, the spread drawn between them.
It is the most interesting number the site produces, it is genuinely novel, and
no competitor has anything like it. It also makes the character system legible
at a glance rather than requiring five cards to be read.

## Component inventory

| Component | Status |
|---|---|
| Icon rail | Built |
| Chart pack: dots, bars, distribution, sparkline, versus | Built |
| Split-bar comparison row | **New** |
| Disagreement chart | **New** |
| Calendar strip | **New** |
| Fixture card, compact | **New**, replaces the accordion |
| Head-to-head table | **New** |
| Odds tier list | Built |

## Build order

1. **Fix the two blockers.** Nothing else matters if promoted clubs read as
   incapable of fouling.
2. **Grid shell and fixture cards.** Biggest single visual improvement.
3. **Head-to-head table.** The decide-for-yourself surface.
4. **Disagreement chart.** The centrepiece.
5. **Light default and rhythm pass.**
6. **Calendar strip.**

## The rule that outranks the rest

Density is welcome where a reader has chosen to look closely. It is not welcome
on arrival. The head-to-head table can be dense; the first screen cannot.

And a prettier surface must never make a number feel more certain than it is.
Every probability keeps its sample size, its band word and its thin-evidence
flag.
