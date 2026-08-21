# Next phase: from machinery to product

**Status: Proposed, 2026-08-21. Supersedes nothing yet. Needs sign-off before building.**

## What is wrong today

The site works and is honest. It is also close to unusable for anyone who is not the person who built it.

**It shows the machinery instead of the answer.** The round page carries roughly 200 numbers: ten fixtures, each with a distribution chart, four line prices, an expected total and an explorer readout. A visitor cannot tell which of those matters, because they all look equally important.

**It answers questions nobody asked.** "Expected fouls 21.47" is the model's internal state, not a thing a person wants. Nobody arrives wondering about the mean of a negative binomial.

**It has no hierarchy.** Every number is the same size, weight and colour, so the eye has nowhere to land.

**It never says what to do.** There is no pick, no shortlist, no "look at these five". The product the project exists to deliver is absent from the page.

**It is austere to the point of cold.** The restraint was deliberate, to avoid looking like a tipster site. It overshot into looking like a debug view.

## What a general user actually wants

In this order:

1. **Who should I look at today?** A short list of players, not a table of fixtures.
2. **Why them?** One sentence a human would say out loud. Not a feature vector.
3. **How sure are you?** A signal they can read in half a second. Not a decimal.
4. **Were you right last time?** The only thing that makes the first three worth reading.

Everything else, the distributions, the calibration curves, the line grids, is *evidence*, and evidence belongs one click down. It should exist, because hiding it would make us the thing we are trying not to be, but it should not be the first thing anyone sees.

**The governing rule for this phase: lead with the pick, put the machinery behind progressive disclosure.**

## Phase 1: the product that does not exist yet

Nothing about the redesign is worth doing until the page has real content to be designed around. Designing a player-picks interface while the only data is match totals guarantees a second redesign.

### 1a. Ingest player data

Two sources, both verified downloads, no scraping.

- `worldfootballR_data`, 81,328 player-match rows, Aug 2017 to Sep 2025, `Fls` and `Fld` 100% populated, plus minutes, position, tackles, interceptions, cards.
- `FPL-Core-Insights`, 2024/25 and 2025/26 complete, updates three times daily, `fouls_committed` and `was_fouled`.

Both need the identity crosswalk, because they name players differently and neither shares an id scheme with the other or with football-data.co.uk. This is exactly the join [ADR-007](decisions/ADR-007-identity-halts-pipeline.md) exists to protect.

### 1b. Expected minutes

**The single highest-leverage missing piece.** A per-90 foul rate says nothing about a bet that settles on one match unless we know how much of the match the player plays. A 0.9 per-90 fouler who plays 25 minutes is a different proposition entirely.

Two-part model: probability of starting, then expected minutes given the role. Both derivable from the appearance history we now hold.

### 1c. Lineups

The hard dependency, and the one with an unsolved data question.

- **Predicted XI** is modellable now from recent starting patterns, rotation behaviour and days of rest. Good enough to publish days ahead, clearly labelled as predicted.
- **Confirmed XI** lands roughly an hour before kickoff and is what turns a decent prediction into a sharp one. **We do not currently have a source for it.** API-Football has it and is suspended. This needs solving and is called out as a blocker rather than assumed away.

Predictions made before and after lineup confirmation are different products and get graded separately, as [07-backtesting.md](07-backtesting.md) already requires.

### 1d. Player foul models

`player_fouls_committed` and `player_fouls_drawn`, the same ladder as match totals: shrunken rate baseline first, then a count regression, and nothing ships that cannot beat the baseline out of sample.

Each character gets its own player model, in its own temperament, reusing the registry.

## Phase 2: information architecture

Only after Phase 1 has content.

### The daily board, which becomes the home page

Today's fixtures and the shortlist across them. Not ten fixture cards. A ranked set of player picks with the fixture as context rather than as the unit.

Each pick shows: player, fixture, the market in words ("to commit 2+ fouls"), a confidence signal, and one sentence of reasoning. Expanding reveals the distribution, the line grid and the fair odds.

### The match page, in the order requested

1. **Graphical area at the top.** Tabbed rather than stacked: foul environment, both sides' recent form, referee context. One chart visible at a time, so the page has a focus.
2. **Key points underneath.** Three or four sentences of what actually matters about this fixture.
3. **Lineups.** Predicted or confirmed, clearly marked which.
4. **Suggestions.** The picks from this fixture with their reasoning.

### Progressive disclosure everywhere

Target: **under 25 numbers visible on first paint**, against roughly 200 today. Everything else one interaction away.

## Phase 3: the design system, second pass

### Confidence stops being a decimal

A general reader cannot act on 0.4487. Replace with a three-level signal, **Strong / Lean / Thin**, backed by a shape as well as a word so it never depends on colour. The underlying probability stays available on expand, and appears in full on the evidence view.

### Every pick carries one human sentence

Generated from whichever feature moved the number most: "Faces a winger who draws 2.8 fouls a game", "Referee runs 12% above average", "Expected 78 minutes". Written from the model, never hand-written, so it cannot drift from what the model actually did.

### Visual direction

The reference point is a serious data publication that ordinary people read willingly, not a betting site and not a terminal. Concretely:

- More space, fewer rules and boxes. Let grouping do the work borders currently do.
- A real type scale with genuine contrast between levels, so hierarchy is visible before anything is read.
- Charts that carry one idea each. Any chart needing a paragraph to explain is the wrong chart.
- Colour used sparingly and meaningfully. Currently everything is the same blue.
- Player and team identity through initials, shirt numbers and club colour accents. No photography, because we have no licence for it.

### Animation, and what it is for

Motion clarifies change. It does not decorate.

**Yes:** staggered entrance on lists so the eye tracks arrival; charts drawing their line on first view; smooth expand and collapse; hover feedback; a clear transition when confirmed lineups replace predicted ones, because that is a genuine state change worth noticing.

**No:** animated counting numbers, which are literally unreadable while animating and are worse than useless on a page about probability. No parallax, no scroll-jacking, no attention-seeking loops.

All of it respects `prefers-reduced-motion`.

## What we actually give people

A fair price alone is weak. It tells a user their odds are 1.75 and leaves them
to find the market, compare, work out whether the difference is enough, and
decide. We have done none of the deciding, which is the part that is hard.

Five things turn this from a reference into a product.

### 1. A price floor, not a fair price

Instead of "fair odds 1.75", publish **"back at 1.90 or better"**.

This matters more than it looks. **Fair odds are break-even**: betting at exactly
1.75 on a 57% shot returns nothing in expectation and loses to variance in
practice. A floor bakes in a required edge, so the user does not have to compute
anything and cannot accidentally take a price that only looks generous.

Proposed margin: 10% above fair. A 57% pick has fair odds 1.75 and a published
floor of 1.93. The margin is a single configurable number, published openly, and
justified by our own calibration error rather than picked to look good.

**This is the most actionable thing we can publish without holding odds data.**

### 2. A definite call

Rank the picks and name the shortlist. The five characters each give an
opinionated set, and a house call sits alongside them. "Here are today's five"
is a product. "Here are 200 probabilities" is a spreadsheet.

### 3. An odds checker

The user pastes the price they can actually see. We tell them immediately
whether it clears the floor and by how much. Entirely client-side, no data
needed, no cost, and it closes the loop we otherwise leave open.

### 4. The full board, per fixture

Every player on both teams, ranked, with their chance of 0 fouls, 1 or more,
2 or more and 3 or more, each with a fair price and a floor. Collapsed by
default, one per team, expandable.

Dense on purpose, and a different kind of dense from the current problem: a
reference table has structure and the reader opens it deliberately. The current
round page has no structure and opens itself.

**Note on the columns.** Bookmakers price cumulative lines, "1+ fouls", not exact
counts, so the cumulative columns are the bettable ones. P(exactly 0) is worth
showing alongside because it is the clearest read on a player who may not be
involved at all.

### 5. The negative call

"Do not back this at anything under 2.40" is genuinely useful and almost nobody
publishes it. It also demonstrates that the model is willing to say no, which is
worth more for trust than another selection.

## Phase 4: character picks

Once players exist, the Equal Risk Slip becomes buildable: five picks per character per matchday, each slip constrained to a combined probability band so every character faces equal difficulty and the comparison is fair. Personality shows in composition, not in cherry-picking easy bets.

## Sequencing

| Order | Work | Blocked by |
|---|---|---|
| 1 | Player data ingest and crosswalk | nothing |
| 2 | Expected minutes model | 1 |
| 3 | Player foul models, backtested | 1, 2 |
| 4 | Predicted lineups | 1 |
| 5 | Confirmed lineups | **an unsolved data source** |
| 6 | Information architecture | 3, 4 |
| 7 | Design system pass | 6 |
| 8 | Character player picks | 3, 6 |

Steps 1 to 3 are the bulk of the work and unlock everything else.

## The interim question

The current site is live and rough. Two options: leave it while Phase 1 is built, or spend a short pass cutting the worst number density so it is not embarrassing in the meantime. Leaving it is defensible, since nobody is looking yet and effort is better spent on the real product.

## Open questions

1. **Where do confirmed lineups come from?** Unsolved and it gates the sharpest version of the product.
2. **Does the daily board replace the round page, or sit alongside it?** A board is what users want; per-fixture detail is what depth-seekers want.
3. **How much machinery stays visible by default?** The honesty principle says show your work. The usability principle says put it one click down. These pull against each other and the balance is a judgement call.
