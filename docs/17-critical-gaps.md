# Critical gaps, 2026-08-22

**Status: Closed, 2026-08-22.** Seven of eight gaps addressed; odds parked.

Eight findings from first real use. Ordered by how much damage each does.

## 1. The squads are wrong, and this poisons everything

**Severity: highest. Nothing else matters until this is fixed.**

Squads are currently "who played for this club in the last 200 days of the data
we hold". The data ends **September 2025**. It is now August 2026.

So the site is naming players who may have transferred, retired or been relegated,
and omitting every summer signing. A prediction about a player who is not in the
squad is not a weak prediction, it is a wrong one.

Worse, no source we hold fixes it. The live feed (FPL-Core-Insights) has 2026/27
folders that are still header-only, because the season started yesterday. Even a
full 2025/26 file would miss the summer window.

**Therefore gaps 1 and 6 are the same problem.** Accurate squads can only come
from lineups, and lineups have to be fetched live. This is the unblocker for the
entire product, not a refinement.

## 2. Our price floors are above what bookmakers actually offer

We publish "take at 1.50+" for a 73% shot. Books price 1+ fouls nearer 1.30.
So the site says no bet on essentially everything, which is useless.

Two honest readings, and they need separating with evidence:

- **The market is right and we are overconfident.** Most likely for the 1+ line,
  which is the most efficiently priced.
- **The value is at other lines.** 2+ and 3+ fouls are priced more loosely, and
  our edge, if it exists, is far likelier to be there.

Actions: publish a **range** rather than a single floor, show where our number
sits against a typical market price, and steer the product toward 2+ and 3+
where a real gap is plausible. Also revisit `EDGE_MARGIN`: 10% may be too
demanding when we cannot measure our own error yet.

## 3. Layout and styling need the overhaul, plus combination picks

Per-fixture, offer a **selection totalling 4, 5 or 6 fouls** across players, so
2+2+2 or 3+2+1 are presented as one buildable ticket. That is closer to how
people actually bet than a list of independent probabilities.

Needs a **normalised chart pack**: a small set of chart types with one shared
visual language, so every graph on the site looks like it came from the same
place. Tabs per fixture to keep it clean.

## 4. Fouls won is a first-class market and is being under-served

The model computes it. The page barely shows it. It should be equal to fouls
committed everywhere: same tables, same picks, same tabs. Different players
entirely, since drawing fouls is a forward and dribbler trait.

## 5. Tables need filtering, searching and tabs

Sort by any column, search a player, switch between committed, won and totals
without leaving the fixture. Currently a static dump.

## 6. Lineups, one hour before kickoff

The unblocker for gap 1. Needs a live source. Candidates, in order of how
promising they look and how much trouble they carry:

- **BBC Sport** fixture pages, published around an hour before kickoff
- **premierleague.com** via the pulselive API, which is unauthenticated and was
  confirmed working, though its terms restrict commercial use
- **API-Football**, which has this natively but is suspended

Needs its own research pass before committing to one.

## 7. Results, as soon as possible after full time

Nothing can be graded without them, and grading is the entire credibility
strategy. football-data.co.uk updates Sunday and Wednesday nights, which is
adequate for weekly review but too slow to feel live. The same source chosen
for lineups will likely carry results.

## 8. The five have never been compared on player picks

**Stated plainly because the site currently implies otherwise.**

The bake-off that ran, and that Bdog won, was on **match totals**: 4,180
walk-forward predictions across ten seasons, each character predicting a week
using only what was knowable beforehand, scored on accuracy and on whether its
stated confidence was honest.

**The player models have had none of that.** They were built, eyeballed, two
bugs were fixed, and they shipped. Until they run through the same harness,
comparing them is opinion, and the page must not imply otherwise.

## Order of work

1. Lineups and current squads (gaps 1 and 6). Everything else is blocked.
2. Results ingestion (gap 7), because grading proves whether any of this works.
3. Player backtest (gap 8), so the five can be compared honestly.
4. Fouls won parity (gap 4).
5. Layout, tabs, filtering, chart pack, combination picks (gaps 3 and 5).
6. Price floor recalibration (gap 2), which needs the backtest first to know
   how wrong we are.
