# The match players table

**Status: Decided 2026-08-29, Oliver's sign-off. The fixture page's one player
table, replacing the explorer's fixture view and the game sheet's player tier.
Registered in [41](41-primitives.md) on shipping.**

The fixture page showed player data three times: the house sheet's lists, the
game sheet's player tier, and "Every player in this game". One table now,
built for speed of reading.

---

## 🎯 What it shows

Every player from both squads. Before confirmed elevens: all players listed,
no bench distinction, a small **XI mark** on the predicted eleven. Once the
sheets land: the confirmed eleven a side, the rest behind **show bench**.

| Column | What | Sort |
|---|---|---|
| Player | name, position, club chip | name |
| XI | predicted or confirmed eleven mark | yes |
| Mins | expected minutes; actual once played | yes |
| Fouls/90 | real (his record) and expected (this match), two figures in one cell | either |
| Fouled/90 | same, fouls won | either |
| Involvements/90 | same, both together | either |
| House | the house slip the player sits on: safe, optimistic, rogue | yes |

**Every column sorts.** Default order: expected fouls per 90, descending.

**Expanded row** (click): the 1+, 2+, 3+ prices for both markets, all eleven
models when Simple is off, the full distribution, thin-evidence and prior
notes. The Expected/Actual toggle goes: a played game shows actual fouls,
fouls won and minutes as their own columns beside the expected ones.

**The house's three slips** sit above the table in the receipt format the
eleven's slips use, so house and models read as the same kind of thing.

---

## 📱 Mobile

No sideways scrolling table. On phones the table shows Player and **one
chosen stat column**, picked from a column chooser above the table (a
segmented control: fouls, fouled, involvements, mins), with the House badge
folded into the player cell. Sorting follows the chosen column. The expanded
row carries everything else.

---

## 🛑 What it replaces

- The explorer's fixture view on the fixture page (the explorer stays as the
  site-wide tool on its own page).
- The game sheet's player tier and its Expected/Actual toggle. The game
  sheet's **team** tier stays: club against club is a different question.
- The house sheet's list form: the tiers move onto the table's rows and the
  house's slips above it.
