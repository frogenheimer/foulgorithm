# Ideas

Things worth doing that we have **not** committed to. Nothing here is on the roadmap. Nothing here is being built.

Append new ideas at the top with a date. When an idea gets picked up it moves to [11-roadmap.md](11-roadmap.md) and the entry here is marked promoted rather than deleted, so the reasoning survives. When an idea is rejected, say why and leave it, because the same idea will occur to us again in six months.

---

## 2026-08-23 — Ideas from the two external audits

Source and full reasoning in [28-external-audit-review.md](28-external-audit-review.md).
The phase 1 items (substitute programme, calibration apparatus, thin-evidence
widening, house-beside-character, manual odds capture) are proposed there, not
here. This entry holds what was judged valuable but not committed.

- **Coarse positional-channel matchups from formation lines.** Advisor 1 wanted
  spatial interaction matrices, which need coordinate data we do not hold. The
  version we CAN test: does a full-back facing a formation with wide wingers
  concede more than facing a narrow midfield, using the formation slots the
  lineup source already gives us? The r = -0.003 pairing test measured player
  quality, not channel geometry, so this is genuinely untested.
- **Match-based rather than calendar decay** for the house half-life (advisor
  1). Calendar decay punishes international breaks and injury absences; decay
  by matches played treats evidence as evidence. Counter-argument to test
  against: regime change happens in calendar time, and a six-month absence
  genuinely stales information. One harness run decides it.
- **Manager and regime-change targeted evaluation** (advisor 2 §39, 83). Alan's
  claimed edge is "new manager or injury crisis" and it has never been tested
  on that subset. Blocked on data we could build by hand: a manager-change CSV
  is roughly 15 rows a season.
- **Hurdle and Poisson-lognormal challengers** for the distribution ladder
  (advisor 2 §57, 59). P(0) may be a minutes-and-role question while
  P(count | count >= 1) is an aggression question. Fits the existing challenger
  protocol; no new data.
- **Referee effects on distribution shape, not just mean** (advisor 2 §43). A
  strict referee may move the zero probability and the tail differently. Cheap
  study on data in hand.
- **Rest and congestion features** (advisor 2 §49). Days since last match and
  matches in the previous 14 days are derivable from fixture dates we hold.
  Listed in 06-modelling as designed features and never actually tested.
- **Substitution endogeneity, crude version** (advisor 2 §18). Fouls and
  minutes may not be independent for starters (a booked or foul-prone player
  gets withdrawn). Full test needs in-match foul timing we lack; the crude
  test, starters' minutes against their own fouls that match, uses data in
  hand.
- **Within-branch minutes distributions** (advisor 2 §17). The mixture already
  captures the zero spike, which was the big win; whether spread around
  minutes-if-start moves anything is an open, probably small, question.
- **Kish effective sample size** alongside `effectiveMatches` (advisor 2 §56).
  Sigma-w is exposure, (sigma-w)^2 / sigma-w^2 is the conventional n_eff. Show
  both or rename. Small.
- **Age curve for Lily** (advisor 1). An age-decay factor for older players
  would sharpen her reputation-lag weakness into something testable. Low value
  until the characters have a longer record.
- **Market-blend challenger, P_final = f(P_model, P_market)** (advisor 2 §29
  and §72, reaffirmed in their reply). Test whether the model adds incremental
  information beyond the market rather than assuming the market is wrong.
  Blocked on price data: only becomes testable once the manual capture page
  has accumulated a real sample, and even then on the tracked lines only.
- **Poisson-lognormal shared intensity, conditional reopen** (advisor 2 reply).
  Stays retired unless the direct pairwise within-match residual correlation
  test in the Phase A evidence pack comes back positive, in which case the
  decomposition's zero was masking cancellation and this is the first
  candidate back on the table.

---

## 2026-08-21 — Public leaderboard, points and a levelling game

**The idea.** Open the competition beyond the five characters. Any user can make predictions, earn points for accuracy, climb a leaderboard, level up, and win weekly rounds. The five emotions become the house players who seed the board rather than the whole product.

**Why it is interesting.**

- **It is a flywheel.** People come back weekly to defend a rank, which is a far stronger retention loop than checking a tips page. Every returning user also generates a public prediction, which makes the site's core content free to produce.
- **It proves the model in public.** If Alan and Tayler sit mid-table against real humans, that is more convincing than any calibration chart. If they dominate, that is the marketing.
- **It is a safer sell, and Oliver is right about that.** Selling access to a prediction game is not selling betting advice. It sidesteps the CAP tipster proofing requirements, which demand predictions be lodged with an independent third party before events, and it sidesteps the Consumer Rights Act problem where an advertised strike rate becomes a contractual promise. See [13-legal-and-ethics.md](13-legal-and-ethics.md).
- **It sits between markets.** Someone who would never place a bet will still play a free prediction game, which widens the audience well past the betting-curious.

**The two risks that would need resolving first.**

1. **Prizes can turn this into a regulated product.** A free-to-enter competition with a genuine skill element sits outside the Gambling Act. Charge for entry and award prizes on an uncertain event and it can become a lottery, or betting. The line is real and it is not intuitive. Any prize element needs a proper opinion before launch, not after.

2. **Gamifying a gambling-adjacent product is exactly what regulators are looking at.** Points, streaks, levels and weekly rounds are engagement mechanics, and engagement mechanics attached to gambling content are under active scrutiny. A streak that punishes a user for not predicting is the kind of thing that reads badly in a complaint. Designing this well means the game rewards *accuracy and honesty*, never volume or frequency.

**What it would need.** Supabase Auth already ships, so accounts exist. It would need a predictions table for users, a scoring job that runs alongside the existing weekly grading, and the leaderboard itself. The scoring should use a proper scoring rule rather than raw hit rate, for the same reason the characters are normalised: rewarding raw hit rate rewards timid predictions and teaches users the wrong thing.

**Status.** Idea only. Revisit once the characters have a real track record, because a leaderboard with nothing to compare against is an empty room.

---

## 2026-08-22 — Championship data for promoted clubs

**The idea.** Ingest EFL Championship player-match data so newly promoted clubs
arrive with a record rather than a positional prior.

**Why it matters more than it sounds.** Three clubs are promoted every August
and currently all of their players fall back to their position's average. That
is honest but blunt: it says a Championship-winning defensive midfielder and his
third-choice understudy foul identically, which is obviously false. This season
it affects Coventry, Hull and one other, so roughly 15% of every gameweek.

**Why it is not free.** Championship fouls are the same problem as Premier
League fouls were: the sources that carry them are the ones already surveyed.
`worldfootballR_data` covers `ENG_M_2nd` on the same release pattern as the
top flight, so the raw data is very likely a single extra download.

**The modelling question is the interesting part**, and it is not solved by
having the data. Championship fouls are not Premier League fouls: refereeing
standards, tempo and quality all differ, so a raw rate would transfer a number
that does not mean the same thing. It needs a fitted discount, estimated from
players who appear in both divisions across a promotion, which is a real
piece of work rather than a column rename.

**Status.** Idea only, deliberately deferred. The current fallback is defensible
and clearly labelled thin, which is a reasonable place to sit while more
valuable work is outstanding.


---

## Positional heatmaps, and what they would need

**Status.** Wanted, blocked on data rather than on effort. Raised 2026-08-23
alongside the interactive pitch, which is built.

The idea: let a reader move a player's average position around the pitch, in
zones rather than pixels, and have that change his expected fouls and which
opposition players he is likely to collide with. A left-back pushed high meets
the winger more often; a holding midfielder dropped deep meets the striker.

### 🛑 Why it cannot be built yet

**We hold position CODES, not coordinates.** The lineup source gives `Right Full
Back` and `Centre Defensive Midfielder`, which places a slot on a formation and
says nothing about where a player actually spends the match. Average-position
and heatmap data lived on FBref and went with the January 2026 Opta
termination. Nothing free replaced it, and it is not in any of the four sources
we currently read.

Building a response curve without that data would mean inventing how fouls vary
with position and presenting the invention as a model. That is the one thing
this project consistently refuses to do.

### ⚠️ And the nearest testable version already failed

The closest question the current data CAN answer is whether facing a specific
dangerous opponent matters: does a defender concede more against a side whose
best foul-winner is exceptional, beyond what that club's overall rate implies?

Measured over 9,419 player-matches, the correlation is **-0.003**. Zero. The
team-level opponent factor already carries all of it, and knowing which of their
players is the good one adds nothing. See the modelling log, 2026-08-23.

That does not kill the heatmap idea. It does mean the effect, if it exists, is
finer than "who is on the pitch" and needs real spatial data to find.

### ✅ What would unblock it

- Event data with pitch coordinates for fouls. StatsBomb open data covers a few
  competitions and not the current Premier League season
- Tracking or average-position data, which is a commercial product
- A season of our own collection, if fouls were ever logged with a location

Until one of those exists, the pitch stays a lineup tool: it changes WHO is
playing, which genuinely moves every number, rather than WHERE they stand, which
we cannot price.
