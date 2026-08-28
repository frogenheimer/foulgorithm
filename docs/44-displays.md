# Displays that are lacking or under-used

**Status: Proposed 2026-08-28. Six items, ordered by value; each becomes
Decided as it ships.** From the display inventory of 28 August (every page,
every table, every chart).

---

## 🎯 The six

### 1. The house sheet's record

**Gap.** The sheet publishes a safe, an optimistic and a rogue shout per
market on every game and nothing tracks how each tier lands. The house has no
scoreboard of its own.

**Build.** Settle grades each tiered pick against the same outcomes the bets
use (they are house claims already in the ledger, keyed by player, market and
line). A `houseRecord` block in `track-record.json`: per tier, picks, landed,
hit rate, and the house's own average price beside it, so a reader sees
"safe: 71% claimed, 68% landed". Surfaces: a strip on Track record, the tier
hit rates in the house sheet's footnote, and vidiprinter lines for the rogue
shouts that land. Tests: grading of tiered picks, the block's shape.

### 2. The referee strip

**Gap.** `matchday.json` carries fouls-versus-league and cards-booked per
referee; the fixture page shows one line and History one chart.

**Build.** A referee strip under the matchup lockup: name, fouls per match
against the league mean, cards per match, matches this season. Same
kit-chip register. Reads existing data; no pipeline change.

### 3. Team pages read the matchday sheet

**Gap.** Rank, form dots and the temper gauge live on fixture pages only.

**Build.** The team page header gains the kit block with its temper gauge and
the league rank for fouls committed and won; a form row of the last five.
Data already in `matchday.json` and `teams.json`.

### 4. Distributions in the open

**Gap.** Each player's full foul-count distribution is computed and shown only
inside an expanded explorer row.

**Build.** On the game sheet's player tier, a small inline distribution per
row (the `Dots` primitive) for the selected market, so the shape of a number
is visible at a glance. Explorer expansion stays for the full grid.

### 5. We said, it was: the season line

**Gap.** "We said 22, it was 27" appears only on played cards.

**Build.** A `Metric` on Track record and a compact line on the homepage's
Where we stand: across the season, mean expected total against mean actual,
and the share of games inside three fouls. `expected_totals` and results are
already stored.

### 6. Boldness, explained

**Gap.** Two columns, one subtitle.

**Build.** A tooltip on the column heads and a paragraph in the Track record
glossary, from one source in `lib/contract.ts` beside the contract copy.

---

## 🚦 Order

1 first: it is the tiers made accountable and it needs pipeline work. 2, 3 and
5 are display-only on existing data and can ship together. 4 and 6 are small.
