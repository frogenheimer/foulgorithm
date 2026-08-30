# The manager as a regime, not a rating

**Status: Proposed 2026-08-30.** Oliver's idea: different managers play
different styles, so "team" alone probably explains less of a side's foul
count than the manager in charge at the time. This is the plan for putting
that into the model without pretending to know more than we do.

> 💡 **The manager effect is mostly already in the team rate.** A club's
> recent matches were played under its current manager, so a fixed
> per-manager factor would count the same thing twice. Where the manager
> matters is the moment he changes, and that is where the data is thinnest.
> So the model treats a change of manager as a break in the club's record,
> not as a number attached to a name.

---

## 🎯 What changes

| Piece | Now | Proposed |
|---|---|---|
| **Team foul baseline** | one rate per club, time-decayed over its own matches | the same rate, reset at each change of manager to a wider prior that shrinks back as games under the new manager arrive |
| **Starting point after a change** | none | the incoming manager's residual at previous clubs (fouls above what those squads' players would predict), weighted by games and capped |
| **Caretakers** | n/a | a caretaker spell is a regime like any other, so the reset is short and the shrinkage fast |
| **What the site says** | nothing | a line on the game sheet: "New manager, 3 games in: the club's rate is still mostly prior" |

---

## 🚦 Build, in order

1. **The tenure table.** `data/reference/managers.yaml`: club, manager,
   from, to, caretaker flag. Hand-kept, about 30 rows a season, every row
   with a source. Nothing else in this doc exists until this does, and it
   has to be checked by a person, because a wrong start date moves a club's
   baseline on the wrong game.
2. **The regime break.** `features/team_context.py` learns the tenure
   table: a club's foul history is weighted within the current regime, and
   the prior widens at a change. One parameter, the shrinkage rate, set by
   the study below.
3. **The style prior.** For a manager with PL history under our data, his
   residual at earlier clubs seeds the new regime's prior. Capped at a few
   percent of the team rate; most managers will sit at zero.
4. **The study.** `backtest/manager_regime_study.py`: walk-forward over the
   history we hold, scored on log loss over the ten games after every
   change of manager against the plain team rate. Ships only on a clear
   win, logged in the modelling log either way. If the break does not beat
   the plain rate by a few percent on those games, the doc closes.
5. **The line on the sheet**, only if 4 passes.

---

## ⚠️ Why this is not first

- **The data does not exist yet.** The tenure table is a research task
  before it is a modelling one, and one nobody has verified.
- **The effect is rare.** Six to ten changes of manager a season, each
  touching ten games: the study has 60 to 100 games to learn from, which
  is enough to test a reset and not enough to fit a style.
- **The gain is bounded.** Even a perfect regime break only helps in the
  weeks after a change; the rest of the season it is the team rate.

Cards (docs/48) has its data on file and its gate written, which is why it
goes first.
