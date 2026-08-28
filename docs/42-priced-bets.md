# The contract, amended: three bets per game, priced by the house

**Status: Decided 2026-08-28, Oliver's sign-off. Effective matchweek 3
(4 to 6 September 2026).** Amends [38](38-the-contract.md): three bets per
model per game stays, the fixed shapes go. Matchweek 2's bets are binding
under the old shapes and settle under them.

> 💡 **The one-line version.** Every competitor still makes three bets on every
> game, but instead of three fixed shapes they make one bet at each of three
> fixed prices, and the house model sets the price. Shape is free. Difficulty
> is not.

---

## 🎯 Why it changes

Under the fixed shapes, every committed bet this round lands about 5 to 6% of
the time by the house's own numbers (six-ones 5.4%, three-twos 5.9%,
two-and-two 6.2%). That is roughly 19 winning bets across 330 a round: some
come in, but any one of them is a 1-in-17 shot and the ladder has no rung a
reader can expect to see land. Oliver, 28 August: "it would be nice if some of
the picks actually came in."

The obvious fix, bets sized by foul units, was priced and does not do it. A
four-unit bet lands 7 to 10%, a six-unit bet 1.4 to 3.2%, which is HARDER than
today, and inside one unit class a 1+-heavy layout is about 1.4 times easier
than a 2+-heavy one, so free layout would quietly reward one shape. The
currency has to be the price itself.

---

## 🚦 The bets

Three per model per game, one at each band. A bet's **price** is the product
of the **house** model's probabilities for its legs.

| Bet | Target | Band | About |
|---|---|---|---|
| **Banker** | 15% | 12% to 20% | 4/1 to 7/1 |
| **Value** | 6% | 4% to 8% | 12/1 to 24/1 |
| **Long** | 2.5% | 1.5% to 4% | 25/1 to 65/1 |

**Layout is free** inside the band: two to six legs, any mix of 1+, 2+ and 3+
on fouls committed or fouls won, either club. A player appears at most once in
a bet: the same player at 1+ and 2+ is one opinion dressed as two. A player may
appear in more than one of the three bets; they are three separate opinions on
the game.

**The house prices, the character chooses.** A character builds its bet from
its own probabilities, hunting the legs where it believes the house is
underpricing, and the finished bet has to sit in the band by the house's
number. Two characters can each commit a banker the house prices at 13% and
believe it is 20% and 30% respectively; the table settles who was right. The
house is the ruler because it is the one calibrated model with a public
record and the same ruler for all eleven, and because a character pricing its
own bets would game the band in one round.

**Temperament stays.** Selection is the unified logic of 38's amendment: own
probability plus the character's lean, clamped to its sway, with the hot-take
floor for everyone. What changes is that the lean now also shapes the bet:
a bold character reaches its band with fewer, bigger legs; a cautious one with
more, smaller ones.

**Binding is unchanged.** The last version published before the game's own
kickoff is the one that counts. A confirmed lineup regenerates all three.

---

## ✅ Scoring

| Result | Rule | Points |
|---|---|---|
| **Win** | every leg lands | 3 |
| **Draw** | the bet falls exactly one foul short in total | 1 |
| **Loss** | anything else | 0 |

Flat points across bands on purpose: everyone places exactly one bet in each
band, so a banker is worth the same to all eleven and so is a long. Rarity is
already rewarded where it belongs, in the boldness columns, which keep the
house price as their currency and stay the tiebreaker behind foul difference.

Foul difference is unchanged: a landed leg counts +1, a miss counts how far
it missed by. The draw rule is stated in fouls rather than legs because bets
no longer share a leg count: "all but one leg" of a two-leg banker and of a
six-leg long are not the same near-miss, "one foul short" is.

**Voids** are unchanged: a leg whose player has no graded outcome is struck
and the bet settles on its remaining legs. A bet reduced below two legs is
void whole.

---

## 🛑 What does not change

- Three bets per model per game, rounds are gameweeks, per-game binding.
- The append-only record. Matchweek 2 settles under the old shapes; old rows
  are scored by the rules of their day, as 38 already provides.
- The house sheet, the crossover, boldness, the vidiprinter's verdict words.
- Cup ties stay exhibitions, unscored.

---

## 🧱 Build

- `publish/league.py`: `build_slates` targets the three bands via the
  house-price builder (`_slip_at_odds`, the retired ladder's mechanism, kept
  for exactly this), replacing the fixed shapes; `join_slates` and `table`
  learn the fouls-based draw and the below-two-legs void.
- `publish/player_round.py`: `_commit_slates` stamps the band and the house
  price on each bet; the payload's `slates.shapes` becomes the three bands.
- Site: slip labels read Banker / Value / Long with the house price and the
  character's own beside it; the bets note on the fixture page and The five's
  table subtitle say the new rule; the vidiprinter prints the band.
- Tests first, in `test_league.py` and `test_v2_selection.py`: every bet in
  band by house price, no player twice in a bet, the one-foul draw, the
  two-leg void, old-shape rows still scoring under the old rule.
