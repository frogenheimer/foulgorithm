# Implementation review, 2026-08-22

**Status: Actioned, 2026-08-22.** See [22-design-rebuild.md](22-design-rebuild.md).

An honest look at what is actually on screen, measured rather than felt.

## What this site is for

Worth restating, because the current build has drifted from it.

**A person arrives with one question: who should I look at today, and at what
price.** Everything else is evidence for that answer or proof we have been
honest before. The site currently answers the question, but slowly, and it makes
the reader work for it.

## The measurements

Rendered at 1440px, one gameweek of content:

| | |
|---|---|
| Page height | **2,600px** |
| Ink coverage, hero | 6.0% |
| Ink coverage, leaderboard | 4.6% |
| Ink coverage, character cards | 4.8% |

**The page is roughly 95% empty and 2,600px tall for a single gameweek.** That
is the whole problem, and it is the opposite of the one we fixed. We went from
200 numbers with no hierarchy to almost no density at all, and sparse is not the
same as clear.

## What is actually wrong

**1. The width is unused.** Content sits in a ~900px column inside a 1440px
viewport. The leaderboard rows have several hundred pixels of nothing between
the player name and the dot array, which reads as a broken table rather than as
generous spacing.

**2. Everything is one vertical column.** Ten fixtures are stacked full-width
accordions. Nothing is side by side, so comparing two fixtures means scrolling
between them and holding numbers in your head.

**3. The dot field is too loud in light mode.** It was meant as faint depth. At
this contrast it reads as texture competing with the content, and light mode is
where it hurts most.

**4. The hero costs 300px to say one sentence.** True and well phrased, and it
does not need a third of the first screen.

**5. Nothing is a centrepiece.** The charts are dot arrays and small bars, all
supporting roles. There is no single graphic worth looking at, which is what
"not nice enough" means in practice.

**6. No calendar.** Specified, not built.

**7. The character card header is cryptic.** "AVERAGE / ALL FIVE LAND / VS PACK"
assumes the reader has read a paragraph three sections earlier.

## The dark theme question

**Light reads better here and should be the default.** Comparing the two
renders, dark suits the marketing references we borrowed from, where the content
is a few large statements. Ours is dense numeric tables, and for those, dark mode
costs legibility: thin numerals on dark backgrounds bloom and lose definition,
which is exactly the wrong trade for a page of probabilities.

Keep both, follow the system preference, but tune light first and treat dark as
the alternate rather than the design target.

## What to change

**Use the width. Three columns, not one.**

```
┌────────────────────────────────────────────────────────────┐
│ CALENDAR STRIP   week toggle, days with football           │
├──────────┬──────────────────────────────┬──────────────────┤
│ LEAGUE   │ FIXTURES, side by side       │ TODAY'S PICKS    │
│ leaders  │ two or three per row         │ ranked, compact  │
│ compact  │ each a card, not an accordion│                  │
└──────────┴──────────────────────────────┴──────────────────┘
```

**Fixtures become a grid of cards, not stacked accordions.** Each card carries
the two clubs, kickoff, referee, expected fouls and the top two or three
players. Clicking opens the detail. Ten fixtures then fit in one or two screens
instead of ten.

**One centrepiece graphic.** The strongest candidate is already computed and
currently buried: **where the five disagree**. A single chart showing each
fixture with five markers and the spread between them is genuinely novel, is the
most interesting number the site produces, and no competitor has anything like
it.

**Tighten the vertical rhythm.** Target roughly half the current height for the
same content. Section gaps from 64px to 40px, leaderboard rows from 60px to 44px.

**Soften the dot field** to near-invisible in light mode, or drop it. It is
decoration and it is currently louder than some of the data.

## Order

1. Three-column shell and the fixture grid. Biggest single improvement.
2. Light as default, dark tuned second.
3. The disagreement chart as the centrepiece.
4. Calendar strip.
5. Vertical rhythm pass.
