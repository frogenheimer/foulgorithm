# Page structure

**Status: Proposed, 2026-08-22.**

## Home, three regions

```
┌──────────────────────────────────────────────────────────────┐
│  CALENDAR  ·  day / week / month toggle                      │
│  clickable fixtures, xFouls per match at a glance            │
├──────────────────┬───────────────────────────────────────────┤
│  LEAGUE STATS    │  THIS GAMEWEEK                            │
│  (left rail)     │  fixtures ranked by expected fouls        │
│                  │                                           │
│  fouls per 90    │  most likely foul involvement             │
│  fouled per 90   │  widest disagreement between the five     │
│  cards per 90    │  confirmed lineups as they land           │
│  filterable      │                                           │
└──────────────────┴───────────────────────────────────────────┘
```

### Calendar

Toggling day, week and month. Buildable: the league API returns the full
season's fixtures, so a month view is real rather than padded.

**One caution.** A month of Premier League fixtures is roughly 40 matches, and a
grid of 40 cells each showing a number is the density problem we just escaped.
Month view should show *which days have football and how much*, not a number per
fixture. Detail arrives on click.

### Left rail: current-season league stats

**Confirmed available**, verified today against the league's own API: season
totals per player for `fouls`, `was_fouled` and `yellow_card`, ranked, for the
current season. That is the live leaderboard, not our nine-month-old history.

Design note: this rail is *context*, not the product. It should be quiet.

### Right: this gameweek

Fixtures ranked by expected total fouls, plus the small facts worth surfacing:
the highest expected foul involvement, and **where the five most disagree**,
which is the most interesting number the site produces and is currently buried.

---

## Cards as a market

Worth doing, and it needs care.

**We already hold the data**: yellows and reds per player per match, across
81,327 rows, and the league API gives current-season totals.

**Model it as binary, not as a count.** "Is he booked" is the useful question:
second yellows and straight reds are rare enough that a count model would spend
its capacity on a tail that almost never occurs. This is already declared in
`markets/base.py` and is why the `family` field exists.

### Compound bets, and the trap in them

"3 fouls and 2 cards" or "5 fouls, no cards" are attractive and are exactly
where naive maths goes wrong.

**Fouls and cards are strongly positively correlated.** A player committing five
fouls is far more likely to be booked than the same player's card rate implies,
because the booking usually *is* one of those fouls. Multiplying
P(5 fouls) × P(no card) will badly understate a foul-heavy player's card risk,
which means it **overstates** the chance of "5 fouls, no cards".

This is the same correlation problem as the combination tickets, but worse,
because there the correlation was between players and merely made us
conservative. Here it runs in the direction that flatters the bet.

**So compound foul-and-card bets need a joint model before they ship.** Offering
them with multiplied marginals would be publishing a number we know is wrong in
the direction that costs money. A toggle in the interface is cheap; the maths
behind it is not.

---

## The five models page

A league table, which the season replay already produces:

| column | meaning |
|---|---|
| Slips landed | all five picks correct that gameweek |
| Legs won | individual picks correct, e.g. Lukić 2+ fouls |
| Leg rate | legs won as a percentage |
| Claimed vs actual | what the model said against what happened |
| Return | at our own fair odds, labelled as self-referential |

**"Claimed vs actual" is the column that matters** and no tipster site has one.
The season replay found Alan overstating his own picks by 9.5 points while being
honest about the field, and Tayler sitting at +0.3. A table showing only hit
rate would have hidden that entirely and made Bdog look like the best model
rather than the boldest one.

---

## Build order

1. **This gameweek panel.** Highest value, all data present.
2. **League stats rail.** Data confirmed available today.
3. **Models league table.** The replay already computes it.
4. **Calendar.** Most design risk, least new information.
5. **Cards market**, binary, standalone.
6. **Compound foul-and-card bets**, only after a joint model exists.
