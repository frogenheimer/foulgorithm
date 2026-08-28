# The contract, amended again: three slips per game, by foul events

**Status: Decided 2026-08-29, Oliver's sign-off, live the same night. Supersedes the
price bands of [42](42-priced-bets.md) before they ever ran. Effective for every
game kicking off from Saturday 29 August 2026; Friday 28 August was played and
settled under the shapes of [38](38-the-contract.md), and a game is scored under
the contract of its kickoff date, never both.**

> 💡 **The one-line version.** Every competitor, and the house, makes three
> slips on every game: **safe** needs four foul events to land, **optimistic**
> five, **rogue** six. Layout is free inside the count. The house's price is
> printed on every slip so the difficulty is never hidden.

---

## 🎯 Why events, not price bands

42 priced the bands by the house model and rejected foul units for two reasons:
a six-unit slip lands less often than the old shapes, and inside one unit
class a 1+-heavy layout is about 1.5 times likelier than a 2+-heavy one. Both
stand. What outweighs them, Oliver, 29 August: a reader understands "this
needs five fouls" and does not understand "a 4 to 8% band", and three fouls in
a game is a bet no bookmaker pays, so the ladder starts at four. The 1.5x
spread inside a class is a character trait, not a loophole, once the house
price is printed on the slip and boldness rewards the rarer layout on the
tiebreak.

Expected landing rates at typical prices (1+ 0.56, 2+ 0.27, 3+ 0.12): safe
about 9%, optimistic about 5%, rogue about 2.5%. Safe is the safest of three,
not safe.

---

## 🚦 The slips

| Slip | Foul events | Legs | Lines allowed |
|---|---|---|---|
| **Safe** | exactly 4 | 2 to 4 | 1+ and 2+ |
| **Optimistic** | exactly 5 | 2 to 5 | 1+ and 2+ |
| **Rogue** | exactly 6 | 2 to 6 | 1+, 2+, and 3+ **only** for a player the house prices at 20/100 or better at 3+ |

A leg's foul events are its line: 1+ is one, 2+ two, 3+ three. A slip's legs
sum to its count exactly. Either market on any leg. A player appears at most
once in a slip; he may appear in more than one of the three.

**3+ is wild, so it is reserved.** It can only appear on the rogue slip, and
only for a genuine high-foul player by the house's own number. A character
cannot reach six events with two 3+ legs on ordinary players.

**The house makes the same three slips**, from its own probabilities, ranked by
its own price with no temperament and no hot-take floor. They are shown in the
same receipt format as the eleven's, graded like them, and recorded in the
house's own record ([44](44-displays.md) item 1). They do not enter the league.

**Characters choose by edge.** Legs are ranked by how far the character's number
sits above the house's, then by preference, exactly as 42 built them; the
target is now a count of events rather than a band. The hot-take floor stays,
swapping at the same line so the count is preserved.

**Binding is unchanged.** Last version before the game's own kickoff.

---

## ✅ Scoring

| Result | Rule | Points |
|---|---|---|
| **Win** | every leg lands | 3 |
| **Draw** | exactly one foul short in total | 1 |
| **Loss** | anything else | 0 |

Foul events make the draw exact: a five-event slip that produced four is a
draw, whatever the layout. Foul difference, boldness and the below-two-legs
void are as in 42.

---

## 🧱 Build

- `models/ensemble.py`: `TIERS` (safe 4, optimistic 5, rogue 6) replace
  `BANDS`; the effective date and `score_priced` stay.
- `publish/league.py`: `_unit_slip` replaces `_priced_bet`: greedy in edge
  order, a leg joins while the count is not exceeded, a leg whose events
  equal the remainder closes the slip, 3+ legs admitted only on the rogue slip
  above the 20/100 floor; `house_slips` builds the house's three from the
  house's own numbers.
- `publish/player_round.py`: each board fixture carries `houseSlips`; the
  payload's shapes list carries `units`.
- Site: slips show the count and the house price; the contract copy in
  `lib/contract.ts` says events; the match players table of [46](46-match-table.md)
  badges the house's rows.
- Tests first: every slip sums to its count, 3+ only where allowed, two to six
  legs, a player once, house price stored, old shapes before the date, the
  house's three slips exist for every game.
