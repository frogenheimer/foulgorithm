# The cups

**Status: Built, 26 August 2026.** Supersedes the hand-fed slate described in
`publish/cup.py`, which is deleted along with `data/cup_fixtures.json`.

The two domestic cups have their own pages: `/league-cup` and `/fa-cup`. Every
tie where we hold match history for both clubs, which now means Premier League
and Championship sides, gets a page of raw record plus one model number.

> 💡 **The rule that shapes everything here.** No player-level foul data exists
> for the Championship at any price. So a tie involving one of those clubs gets
> a team record, a referee record, a pairing history and an expected match
> total, and it never gets a player pick. A pick built without player data is a
> positional average wearing a probability.

---

## 🎯 What each tie carries

| Tie | Record | Match total | Player picks |
|---|---|---|---|
| Premier League v Premier League | ✅ | ✅ | ✅ |
| Premier League v Championship | ✅ | ✅ | 🚫 |
| Championship v Championship | ✅ | ✅ | 🚫 |
| Anything involving a lower-tier club | 🚫 dropped from the slate entirely | | |

An FA Cup third round is 64 clubs and we hold 44 of the 92 league clubs, so
most of a round is dropped. That is the normal case, not a failure, and it
happens silently.

---

## 🔌 Where the data comes from

**The slate, the referee and the elevens** come from the Premier League's own
API, which carries the FA Cup (competition 4) and the EFL Cup (competition 5)
alongside its own league. Free, no key, no card, no daily quota, and already
this project's lineup source, so the cups add no new account to keep alive.

Two things it will not give us:

- **The referee before kickoff.** `matchOfficials` is empty on an upcoming
  fixture and populated from kickoff onward. So most tie pages carry no
  official, and they say "not appointed yet" rather than dropping the block: a
  missing block reads as "we hold nothing on this referee", and we hold 48 of
  them back to 2000/01.
- **`teamLists` as an empty list.** Before the sheets land it is
  `[null, null]`, two placeholders. Calling `.get()` on those raises.

**Both clubs' records come from football-data.co.uk**, E0 and E1 alike. This is the
whole reason the comparison is honest: a page half built from API-Football
player rows and half from a CSV would not be a comparison. Six team stats a
match plus the referee, back to 2000/01 in both divisions.

The published window is this season and last, matching the league team pages.
A club that changed division inside it keeps its **spells** apart, so the page
reads "38 in the Premier League, 8 in the Championship" rather than pooling two
leagues silently.

---

## ⚠️ Why raw numbers alone would mislead

The trap is not the one people expect. Over the published window the Premier
League averages **10.75** fouls a match and the Championship **10.81**, which
is nothing. `features/promotion.py` has said for years that the level ratio is
0.990 and that it is a red herring.

**The spread is what differs.** Premier League club rates have a standard
deviation of 0.70; Championship rates 0.98, about 40% wider. So "+1.4 above
average" is a materially bigger claim in one league than the other, and a
reader cannot see which from the number.

Two things travel with every value, and neither adjusts it:

- **The division average**, named: "+1.4 v Championship".
- **The rank inside that division**: "3rd most in the Championship of 24".
  Rank is the one that survives the spread problem, because 3rd of 24 means the
  same thing in any league.

A cross-division tie also carries a callout saying the two columns are two
different scales. Nothing is normalised. Normalising would be a model judgement
inside a section that has none.

---

## 🧱 The one model number

Expected total fouls, from `models/cup_totals.CupTotal`. Total fouls is a team
quantity and football-data covers both divisions, so unlike a player pick it is
supportable.

`match_features._team_rate` returns the league average for a club with no rows
in the match store, so an unadjusted model would hand a Championship club
exactly average Premier League behaviour and publish it as a read on that club.
Silently average is the failure this project exists not to make. Instead:

- A second-tier club's own record is shrunk onto the top-flight scale via
  `promotion.second_tier_prior`, at the fitted **beta 0.373 over 66 promotions**.
- Only the deviation crosses. Carrying the raw level scores **16% worse** than
  using the league mean, which is counter-intuitive precisely because the two
  divisions' means are nearly identical.
- A club with no measurable second-tier season is named in `unpriced` on the
  page, rather than quietly priced off the mean.

A tie between two Premier League clubs produces the champion model's number to
the decimal, because a cup tie between two top-flight clubs is a league game
and the model has no reason to treat it differently.

---

## ✅ Separation

The 25 August 2026 collision, where the League Cup's Nott'm Forest v Leeds took
over the league fixture's page, was fixed with a `-cup` suffix. That created a
smaller version of the same bug: two cups means the same pairing can happen in
both, and both landed on one URL again.

| Competition | Slug |
|---|---|
| League | `arsenal-v-chelsea` |
| League Cup | `arsenal-v-chelsea-league-cup` |
| FA Cup | `arsenal-v-chelsea-fa-cup` |
| Replay or second leg | `arsenal-v-chelsea-fa-cup-2`, numbered in kickoff order |

The fixture key is `(home, away, competition, kickoff)`, never the label.

---

## 🚦 The lineup watch

`jobs/cup_watch.py`, on the same weekly reschedule as the league's. Opens at
T-70 because cup elevens are no more punctual than the league's T-60, gives up
at kickoff, and polls every three minutes.

The old version of this job had a request-budget problem worth remembering,
because the fix was to change source rather than to optimise. It polled
API-Football per fixture every 90 seconds: about 47 requests for the single
hand-fed tie it was written for, and roughly **470 for a ten-tie round against
a free cap of 100 a day**. It would have died four fifths of the way through
and produced no elevens at all, which is worse than producing them for one tie.

The league's API needs no key and meters no daily quota, so that whole problem
is gone rather than solved. Polling stays gentle anyway, because the source is
free and somebody else pays to run it.

---

## 🛑 Still exhibition

Nothing here is recorded, graded or scored. No claims, no slates, no league
scoring, no track-record noise from games our results source will never grade.
The payload says `recorded: false` out loud rather than leaving it to a
docstring. The contract is a league of Premier League gameweeks (docs/38), and
a cup night is not quietly a fourth bet in it.
