# Cards: a bonus area, house only

**Status: Proposed 2026-08-29, for Oliver's sign-off.** A card section on the
fixture page from the house model only, kept out of the league, and built
on what the repo has already measured about cards rather than around it.

> 💡 **The constraint that shapes this.** Player bookings are close to
> unpredictable with what we hold: the best variant beat a league base rate by
> 0.5% (modelling log, 22 August). Team-level card totals and referees are a
> different story. So the bonus leads with the match, not the man, and every
> player figure sits beside the base rate it barely beats.

---

## 🎯 What we can say honestly

| Layer | Evidence | What we publish |
|---|---|---|
| **Match total cards** | 26 seasons of team card rates from football-data; referee cards per match and fouls-booked share already in `matchday.json`; referee variance is real | An expected total and a price on the common lines (over 3.5, over 4.5), **gated**: ships only if the walk-forward test beats the league base rate meaningfully |
| **Team cards** | Same, per club, home and away | Expected cards a side, beside the season rate |
| **Player bookings** | 81k player-matches with yellows and reds; position priors are large (defensive midfielders 21.5% against 13.9%); own record adds 0.5% | A **booking-risk board**, five names a side ranked by shrunk own rate on a position prior, each shown beside the league base rate and marked weak evidence. A ranking, never a pick |
| **Red cards** | 0.4% of appearances | Nothing per player. A match-level "sending-off" chance from team and referee rates only, if the gate passes |

**Not in the league.** No character makes card slips; the house's card figures
are a bonus panel and never score points or boldness.

---

## 🎯 The call on 30 August

Oliver asked for this and the manager regime (docs/52) to be planned side
by side and the easier one actioned first. Cards goes first: the card
history is on file (26 seasons of team rates, 81k player-matches, referee
cards per match already in `matchday.json`), the gate study is specified
below, and the settle window can carry bookings as soon as the snapshot
asks for them. The manager regime has no data yet and a rare effect.

The plan, in brief:

- **House only, fixture page, bonus area.** Nothing in the league, nothing
  graded into the table.
- **Lead with the match.** Expected total cards and per club, from the
  referee's rate and each club's, next to the referee strip that exists.
- **Referee gated.** No card figure until the referee is named.
- **Player bookings as a risk board.** Each name beside the base rate,
  marked weak; a ranking, never a shout.
- **Grade it from day one.** Bookings settle from the same window rows as
  fouls, so the house card record accrues before anything is promised.
- **A fourth house slip only if the gate passes.**

Today's action is step 1 of the build order: `yellow_card` and `red_card`
into the season-totals snapshot and the settle window. Steps 2 to 4 follow
the gate.

**Step 1 shipped 31 August.** Two things worth knowing about the first
rounds:

- **Cards start unknown, not zero.** Bookings ride along exactly as
  minutes do (`settle._rider`): a stat is differenced only when BOTH
  snapshots carry it, or the player is absent from the earlier one
  entirely. The snapshot on file predates the stat, so tonight's settle
  records `null` bookings for every player already in it and real ones only
  for debutants. The first window with cards known for everyone is the one
  after tonight's, next weekend. A zero there would have said a player
  finished last week on no bookings and was booked tonight.
- **An empty stat table is refused.** A card table that comes back with
  nobody in it means the endpoint moved, not that nobody was booked, and
  written as zeros it would say "no bookings" every week, quietly, since
  nothing is published on a card yet to make it visible. The stat is
  omitted, which reads as unknown and self-heals. An empty `fouls`,
  `was_fouled` or `appearances` table raises instead: those are the job.

---

## 🚦 Build, in order

1. **Data first.** Add `yellow_card` and `red_card` to the season-totals
   snapshot (`sources/player_season_stats.STATS`): the league's API posts
   them per player, so settle's diff yields a booking outcome per player per
   match from the next matchday on. Team cards for grading totals come from
   football-data as they do for fouls.
2. **The gate study.** `backtest/card_totals_study.py`: walk-forward over the
   match history, team card rates with time decay, a hard-shrunk referee
   factor, a negative binomial over the total; scored on log loss at 3.5
   and 4.5 and on calibration against the league base rate. Ships only on a
   clear win, logged either way.
3. **The panel.** `CardsBonus` on the fixture page under the house's slips:
   expected total with the referee's line beside it ("Barrott books 19% of
   fouls, 3.7 cards a match"), the two team figures, the booking-risk board.
   One primitive, registered in 41; the referee strip of 44 folds into it.
4. **Grading.** Settle grades the match total and each named booking; a
   "cards" block in the track record with claimed against happened, so the
   0.5% claim is checked in public rather than assumed.
5. **Later, if the gate passes**: a fourth house slip, "cards", never a
   character's.

---

## ⚠️ What this is not

Not a route to bookmaker prices: the study closed that door, since 0.5% over
base rate does not survive a margin. Not a per-player probability the site
stands behind. A reader who wants to know who is likely to be booked gets the
honest answer: position, record, base rate, and "weak".
