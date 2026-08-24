# Addendum: one audit blocker is no longer a blocker

**Written 2026-08-24, after the data work recorded in
[28-foul-data-sources.md](../28-foul-data-sources.md).**

Two of the three responses in this folder rest partly on what data existed. One
of those claims has stopped being true, and it should be re-read before the next
round of model work rather than after.

---

## 🎯 §36 to 38 is unblocked

The response to advisor 2 registered role, style and team-tactics features as
*"right lens, blocked on data: take-ons, carries, PPDA and possession all died
with the January 2026 Opta termination and nothing free replaced them."*

**Something free did replace them, and it was already in the codebase.** The
league's own API carries all of it, back to 2006/07, at team and player level.
Every stat named as dead, checked:

| Stat | Team level | Player level |
|---|---|---|
| `possession_percentage` | present | team only, as it should be |
| `total_contest`, `won_contest` (take-ons) | present | **present** |
| `touches`, `touches_in_final_third`, `touches_in_opp_box` | present | **present** |
| `poss_won_def_3rd` / `mid_3rd` / `att_3rd` | present | **present** |
| `total_tackle`, `duel_won`, `aerial_won` | present | **present** |
| `final_third_entries`, `pen_area_entries` | present | not fetched, one command away |
| `poss_lost_all`, `dispossessed` | present | **present** |

**PPDA is computable.** It needs opposition passes over defensive actions, and
`opposition_passes`, `total_tackle`, `interception` and `fk_foul_lost` are all
present. Median across the sample is 8.7, which is the right order for a
pressing metric and a sign the fields mean what they say.

So the lens the audit called right is now affordable. Whether it *helps* is
still an open measurement, and the audit's own promotion discipline applies.

## ✅ The shared match effect: independently confirmed

Section 5 pushes back on §14 and §61 to 62, retiring the shared match effect
"by measurement". That measurement has now been repeated from scratch, by
someone who did not know it had been done, and it agrees.

Across three characters and two windows: the house model's predictive variance
for a match total is **26.93 against an actual 24.43**, so there is nothing
missing to add and adding some would make an already slightly-too-wide
distribution worse. Slope ranges 0.44 to 2.00 depending on which character you
ask, which is why a single figure was misleading in the first place.

Full working in [25-match-variance.md](../25-match-variance.md). The
disagreement is not with the pushback; it is with the original plan, and the
pushback was right.

## 📊 What is on disk now

| Set | Size | Span |
|---|---|---|
| Player-matches, six leagues | 485,569 rows, 8,968 players (was 81,327 and 1,671) | 2017 to Sep 2025 |
| Player-seasons, league API | 18,143 rows, **67 columns** | 2001/02 to 2026/27 |
| **Team matches, league API** | **15,200 rows, 269 columns, 7,600 fixtures** | **2006/07 to 2025/26** |
| Championship team data | 26 seasons | already in use |

All under `data/raw/`, all gitignored and refetchable, all with provenance.

## ⚠️ Two numbers any model touching this must carry

1. **The provider offset is +4.6%.** The league API reads 3.4% to 6.4% above the
   FBref archive on England fouls, every season, never once lower. Both track
   the same year-to-year movement, so it is definitional rather than error.
   Mixing them without this term moves every published number by five percent.
2. **England is the outlier among leagues, not the yardstick.** Every other
   league runs 12% to 25% above it, against a 9% spread across England's own
   eight seasons. Pooling needs a fitted league intercept, and
   [29-why-leagues-differ.md](../29-why-leagues-differ.md) shows it is not
   explained by how much each league tackles.

## 🛑 What did NOT change

- **The TIME gap, not the volume.** Per-match player data improved a great deal:
  81,327 rows to 485,569, and 376 to 432 of the 570 current Premier League
  squad players now have a per-match record, 57 of them gained from their time
  abroad. What did not move is the calendar. All six league files stop on 14
  September 2025, so nothing covers October 2025 onwards, and that window
  **cannot be recovered backwards**: every gameweek filter the API accepts is
  silently discarded. Only seasons we snapshot through will ever have match
  detail, so every week the settle job does not run is lost permanently.
- Second-tier player data still does not exist free, confirmed from two
  directions. Promoted-club squads remain roughly three quarters invisible, now
  partly mitigated by the club-relative prior shipped 2026-08-24.
- Bookmaker prices are still the missing signal, and no amount of this data
  substitutes for them.
