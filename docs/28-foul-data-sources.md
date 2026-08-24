# Where foul data can actually be obtained

**Status: Researched 2026-08-24. Every figure here was verified by fetching the
source, not recalled.** No code changed on the back of it; this is the survey the
decisions rest on.

---

## 🎯 The short version

| Level | Source | Coverage | Live? |
|---|---|---|---|
| **Team fouls per match** | football-data.co.uk | 2000 to now, **12+ leagues** | **yes** |
| **Player fouls per match** | worldfootballR mirror | 2017 to Sep 2025, **6 leagues** | no, archived |
| **Player fouls, season totals** | Premier League tables | **2006/07 to now, 20 seasons** | **yes** |
| Player fouls per match | FBref direct | — | blocked |
| Player fouls | FPL | — | **does not exist** |
| Player events incl. fouls | StatsBomb open data | 2 PL seasons | no |

Two things follow, and they are different problems that get confused:

1. **Volume** is solvable and free. Five more leagues of player-level fouls are
   sitting in the same archive we already use, about 450,000 player-matches
   against the 81,000 we read today.
2. **Recency** is not solvable for free at player level *per match*. Everything
   in that archive froze on the same day. But per-player season RATES are
   complete and current from the league itself, back to 2006/07, which covers
   every gap we have and eleven seasons before our archive begins.

---

## 🚦 What went wrong

Nothing in this pipeline. One upstream source died and there was no second.

Player data comes from **worldfootballR**, an R project that scraped FBref and
published the results as CSV files on GitHub releases. That project is now
**archived**: last push 2025-09-18, and none of its twenty forks has pushed
since. FBref itself sits behind a Cloudflare interactive challenge.

The gaps in our file are therefore two different things, and only one is a fault:

| Gap | Cause |
|---|---|
| May to Aug, every year | Close season. Not a gap |
| Mar to Jun 2020 | COVID suspension. Not a gap |
| Nov to Dec 2022 | Qatar World Cup break. Not a gap |
| **Apr to May 2022** | **A real hole: 75 of 380 matches of 2021/22 missing. Found 2026-08-24 by the provider study, when the league's own totals read consistently higher than ours for that season alone** |
| 2022/23 | 7 matches missing. Same discovery |
| **Feb to May 2025** | **A real hole in the upstream collection, ~141 matches** |
| **After 14 Sep 2025** | **The archive stopped. ~340 matches and counting** |

## ⚠️ The FBref confusion, resolved

Worth stating plainly because it is genuinely confusing.

**The 81,327 player-matches we hold came FROM FBref.** They were harvested by
worldfootballR before the wall went up and published as files on GitHub. Those
files are still downloadable, because they live on GitHub rather than FBref.

**What is blocked is asking FBref for anything new**, including old matches. The
match pages still render in a browser, which is why the data looks obtainable,
but every programmatic route returns a Cloudflare challenge. Verified: `curl`
with a browser user agent gets HTTP 403, headless Chrome gets the challenge page,
and even `robots.txt` is gated.

So "historical FBref data" is obtainable, and we already obtained it. There is no
more of it to be had from that direction, at any price. Stathead is a paid tier
of the same site behind the same wall.

---

## ✅ What is obtainable, verified

### Team fouls, everywhere, still live

`football-data.co.uk` publishes `HF` and `AF`, home and away fouls, per match,
free, no key, no blocking. **We already ingest this and hold 9,880 matches back
to 2000**, including every match our player data is missing: 572 matches since
January 2025, all 572 with fouls.

Fouls are present for the current season in at least twelve competitions:

| Code | League | Matches this season |
|---|---|---|
| E0, E1, E2 | Premier League, Championship, League One | 380, 552, 552 |
| SP1, I1, D1, F1 | Spain, Italy, Germany, France | 380, 380, 306, 306 |
| N1, P1, T1, B1, SC0 | Netherlands, Portugal, Turkey, Belgium, Scotland | ~300 each |

This is the only live, free, unrestricted foul source found. It is team level,
which is a real limitation and not a fatal one: see the model note below.

### Player fouls, five more leagues, same archive

The `fb_advanced_match_stats` release holds **168 assets**, of which 24 are the
`misc` files that carry fouls. We read exactly one of them.

| League | Rows | Players |
|---|---|---|
| England (in use) | 81,327 | 1,671 |
| **Italy** (verified) | **77,736** | **1,820** |
| Spain, Germany, France, USA | not downloaded, comparable file sizes | |

Schema is identical: `Fls` fouls committed, `Fld` fouled, plus `Min`, `Pos`,
`CrdY`, `TklW`, `Int`, aerial duels. Serie A is 100% populated for fouls across
2017 to 2025, nine season labels.

Pulling all six is roughly **450,000 player-matches**, a 5.5x increase, for the
cost of five downloads of about 40 MB each. Every one froze in September 2025.

### Player fouls, EVERY season back to 2006/07, from the league itself

**The most useful thing in this survey, and it was sitting in a source we
already call.** `stats/ranked/players/fouls` takes a `compSeasons` parameter and
the league exposes 35 season ids. Tested season by season:

| Season | Players with fouls |
|---|---|
| 2026/27 (in progress) | 142 |
| 2021/22 | 469 |
| 2016/17 | 462 |
| 2011/12 | 472 |
| **2006/07** | **477** |
| 2005/06 and earlier | **0** |

**2006/07 is the boundary.** That is **twenty complete seasons** of official
per-player foul and fouls-drawn totals, free, no key, no blocking, from the
league that ran the matches.

Our own archive starts in 2017/18. This reaches **eleven seasons further back
than anything we hold**, and it covers both gaps in it: the Feb to May 2025 hole
and the whole of 2025-26.

**The limit is granularity, not history.** These are SEASON TOTALS. A single
match is recoverable only as the difference between two snapshots, which is what
`jobs/settle.py` does going forward. It cannot be done backwards, because the
league only ever published the running total and nobody was snapshotting in
2019.

So it completes every player RATE and adds no per-match training rows. Given the
player's own rate is the largest single input to a prediction, that is a much
better trade than it first sounds.

### What else comes with it, and at what cost

**Minutes are there**, so everything can be a rate rather than a count:
`mins_played` returns 562 players for 2024/25 and is present in all twenty
seasons alongside `appearances`.

**Thirty-nine player stats respond**, tested one by one against 2024/25. The
ones that matter for a foul model:

| Group | Stats |
|---|---|
| **Denominators** | `mins_played`, `appearances`, `touches`, `total_pass` |
| **Targets** | `fouls`, `was_fouled`, `fouled_final_third` |
| **Discipline** | `yellow_card`, `red_card`, `penalty_conceded` |
| **Tackling** | `total_tackle`, `won_tackle`, `attempted_tackle_foul`, `challenge_lost` |
| **Duels** | `duel_won`, `duel_lost`, `aerial_won`, `aerial_lost` |
| **Carrying** | `total_contest`, `won_contest`, `dispossessed`, `unsuccessful_touch` |
| **Position of play** | `poss_won_def_3rd`, `poss_won_mid_3rd`, `poss_won_att_3rd`, `touches_in_opp_box` |
| **Defending** | `interception`, `interception_won`, `total_clearance`, `head_clearance`, `ball_recovery` |

`attempted_tackle_foul` is worth calling out: a tackle attempt that became a
foul, which is nearly the mechanism the model is trying to predict.

Four team-level names do NOT work per player: `total_yel_card`, `fk_foul_lost`,
`fk_foul_won`, `possession_percentage`. The first three have player equivalents
under different names; possession is inherently a team quantity.

**Fetch cost.** `pageSize=500` returns a whole season in one request, about 2.5
seconds. Twenty seasons times twenty stats is 400 requests, roughly seventeen
minutes, once. The default `pageSize=100` would make it 2,000.

### Why recent matches have per-player fouls and old ones do not

**Not archiving. The league has never published per-match player stats, in any
season.** Verified above: no player-scoped match endpoint exists, and lineups
carry identity only.

What exists for recent matches is manufactured here. `jobs/settle.py` snapshots
the season totals, and a player's fouls in one match are the difference between
two snapshots taken either side of it. Old seasons expose exactly the same
totals; there is simply only one reading of them, and a single reading cannot be
differenced.

So the asymmetry is ours, not theirs. Every season back to 2006/07 is equally
available as totals, and only the seasons we snapshot through will ever have
per-match detail.

**And we cannot snapshot backwards.** A snapshot is a reading of the running
total right now, and the API only ever reports the current or final figure.
Tested and all silently ignored: `gameWeek`, `gameweek`, `matchweek`, `week`,
`gameWeeks`, `fixtures`. Each returns the identical 476 entries with the same
season-top value, so the filter is not merely unsupported, it is accepted and
discarded, which would have been an easy way to fool ourselves. There is no
as-of-date parameter and `stats/player/{id}` returns season or career totals
rather than a match history.

The 2025-26 season is therefore permanently unrecoverable at match level, and so
is every season before it. Only 2026-27 onwards can be built, one round at a
time, by a settle job that actually runs.

### Still available and not taken: 180 team stats a match, twenty seasons

**The largest unclaimed thing found.** `stats/match/{id}` works for historical
fixtures, not just current ones, and the fixture list is available per season.

| Season | Stats across both teams | Fouls present |
|---|---|---|
| 2006/07 | 212 | yes |
| 2012/13 | 250 | yes |
| 2016/17 | 303 | yes |
| 2024/25 | ~340 | yes |

Around 180 stats per team per match, back to the same 2006/07 boundary, and it
carries `fk_foul_lost`, `fk_foul_won`, `attempted_tackle_foul` and
`fouled_final_third` throughout.

**We currently hold about six team stats a match** from football-data.co.uk:
fouls, cards, shots, shots on target, corners, goals. This is roughly thirty
times richer, adding possession, touches by third, duels, aerials, tackles,
clearances, recoveries and where on the pitch possession changed hands.

**Cost: about eighteen minutes.** 20 seasons times 380 fixtures is 7,600
requests at 0.14 seconds each, which is ten times faster per call than the
ranked-player endpoint. A one-off background job.

This would substantially expand roadmap item 9, which currently proposes only
moving the opponent and referee factors onto live team data. With this the
opponent model could use how a side actually plays rather than how many fouls it
concedes.

### What was deliberately NOT fetched, and how to add it

A sweep of all 185 team-level stat names against the player endpoint found
**158 respond at player level**. We fetch 45. The remaining ~113 were skipped on
relevance rather than cost, and are recorded here so nobody has to rediscover
them.

| Group | Roughly | Examples | Why skipped |
|---|---|---|---|
| Shooting | 68 | `att_ibox_target`, `total_scoring_att`, `goals_conceded_ibox`, `big_chance_missed` | A foul model has little use for shot placement |
| Passing | 36 | `total_pass`, `accurate_pass`, `fwd_pass`, `passes_left`, `crosses_18yard` | Style proxies at best, and we already hold `touches` |
| Other | ~46 | `final_third_entries`, `pen_area_entries`, `wins`, `formation_used`, `total_offside` | Mixed. The first two are the most plausible future additions |

**Adding any of them costs about a minute per stat**, across every season:

```
python -m foulgorithm.sources.league_seasons --backfill
```

`backfill_stats()` reads which stats each season file already holds and fetches
only what is absent, so adding one column does not mean re-fetching twenty
seasons. Add the name to `STATS` in `sources/league_seasons.py` and run it.

**The two worth adding first**, if a model ever wants attacking volume rather
than defensive: `final_third_entries` and `pen_area_entries`. Both plausibly
drive fouls WON, which is the market we model worst.

### Other competitions, and the one that is missing

The API exposes twelve competitions: Premier League, Champions League, Europa
League, FA Cup, EFL Cup, Premier League 2 and various youth leagues.

**There is no Championship**, which belongs to the EFL rather than the Premier
League, confirming from a second direction that second-tier player data has no
free route. Cup competitions are available and deliberately not taken: mixed-tier
opposition would need its own handling and is more likely to pollute a foul model
than improve it.

### What the league does NOT publish

Checked, so nobody checks again:

- `fixtures/{id}` carries `teamLists`, and a lineup entry has identity only:
  age, id, name, `matchPosition`, shirt number. **No statistics.**
- `events` on a fixture covers goals, bookings, substitutions and period
  markers. **No foul events.**
- `stats/match/{id}` is real and rich, 169 stats per team including
  `fk_foul_lost` and `fk_foul_won`, **but it is team level**. `?type=player`
  returns the same team payload.
- `stats/match/{id}/players`, `stats/players/match/{id}` and
  `fixtures/{id}/players` all return 404.

Per-player, per-match foul data does not exist in this API at any depth.

---

## 🛑 What was ruled out

- **FPL.** Checked the API directly: there is no foul field, in bootstrap or
  element-summary. It carries `tackles`, `yellow_cards`, `red_cards` and
  `clearances_blocks_interceptions`. Fouls contribute to the bonus points system
  but BPS cannot be inverted to recover them. **FPL is not a foul source.**
- **FBref and Stathead.** Cloudflare interactive challenge, described above.
  Paying does not move the wall.
- **StatsBomb open data.** Free and extremely rich, event level with
  coordinates, but only **two Premier League seasons**. Eighteen seasons of La
  Liga and Champions League make it interesting for the positional questions in
  `docs/ideas.md`, not for this gap.
- **API-Football.** Carries exactly what we need per fixture. Account currently
  suspended; a new key changed nothing, so it is the account rather than the
  credential. RapidAPI resells the same data under a separate account, which is
  the obvious route back in.

---

## 🏟️ The Championship, and the promoted clubs

**Team level: already held and already used.** 26 seasons of `E1` sit in
`data/raw/football_data/`, and `features/promotion.py` turns them into a prior
for each promoted club. It works: Coventry 10.41, Hull 11.08 and Ipswich 10.98
fouls per match against a league mean of 10.82.

**Player level: does not exist for free.** The archive release holds `_1st` tier
files only, for all six leagues. There is no `ENG_M_2nd`, and FBref, where such
data would come from, is walled.

The cost of that gap is not small:

| Club | Squad | With a PL record | Without |
|---|---|---|---|
| Arsenal | 29 | 28 | **1** |
| Liverpool | 34 | 23 | 11 |
| Ipswich | 31 | 15 | 16 |
| Hull | 31 | 8 | **23** |
| Coventry | 31 | 7 | **24** |

**Roughly three quarters of a promoted club's squad is invisible at player
level**, against three percent of Arsenal's. Those players fall back to a
position average, so every Coventry defender is currently priced identically.

### A free improvement nobody has taken

We hold each promoted club's **team** foul rate from the Championship, and it
already produces a club-level prior. It is not used on that club's own players.

A Coventry defender could be priced as *the position average, scaled by how
Coventry's Championship foul rate compares to the Championship average*, rather
than as the bare position average. It distinguishes a disciplined promoted side
from a dirty one, which is the whole of what we can honestly say about a player
we have never seen.

Cheap, uses only data on disk, and strictly better than treating three squads as
interchangeable. Worth a measurement before belief, like everything else here.

## 🗃️ The old foulgorithm repository

Checked at `~/Documents/Foulgorithm`. 250 CSVs, and the answer is: marginal.

| What is there | Shape | Verdict |
|---|---|---|
| `team_player_stats/` | 557 players, 20 clubs, **season aggregates** | small but useful |
| `team_fixture_stats_previous_seasons/` | team per-fixture, 21-22 to 23-24, FBref columns | duplicates what we hold |
| `GW*/foul_picks_*.csv` | old model OUTPUT | not source data |

**The player file is a snapshot, not history.** One row per player with `Fls`,
`Fld` and `90s` for the season to date. No date column, so a foul cannot be
attributed to a match, and it cannot add training rows.

It is still worth something. File dated **5 April 2025**, 6,565 ninetys, top
player on 30, so it is 2024-25 to roughly matchweek 30. Our per-match data for
that season stops on **3 February 2025**. The difference between the two is
aggregate fouls per player for **February to April 2025**, about eight
matchweeks that are otherwise entirely missing. Implied rate 1.014 per 90, which
sits inside the England range and is a decent sign it is not corrupt.

So: it patches a rate for one window of one season. It does not restore history.

## 🔌 Libraries that scrape, and why they do not help

`probberechts/soccerdata` is actively maintained, 2,000 stars, and carries
readers for FBref, Sofascore, WhoScored, Understat, ESPN and football-data.co.uk.
Sofascore and WhoScored both publish player fouls per match and both are live,
which makes this the most promising lead found.

It does not survive contact. **Sofascore's API returns HTTP 403 to a plain
request** with a browser user agent, the same as FBref. Libraries reach it by
impersonating a browser at the TLS level, which is the same category of
circumvention as solving the Cloudflare challenge, so it is ruled out on the same
grounds rather than on a different one.

Worth stating explicitly: the blocker is not that these sources lack the data or
that finding them is hard. Every live player-level foul source found is either
behind a bot wall or behind a paid account. That is the actual constraint.

## 🧮 What was actually fetched, and the two offsets that came with it

**Fetched 2026-08-24.** Both sets are on disk with provenance.

| Set | Size | Span |
|---|---|---|
| Player-matches, six leagues | **485,569 rows, 8,968 players** | 2017 to Sep 2025 |
| Player-seasons, league API | **13,419 rows, 3,916 players, 49 columns** | 2001/02 to 2026/27 |

Player-matches by league, and the reason a league column is mandatory:

| League | Rows | Players | Fouls/90 | vs England |
|---|---|---|---|---|
| **England** | 81,327 | 1,671 | **0.972** | — |
| USA | 90,080 | 1,907 | 1.092 | +12% |
| Germany | 69,668 | 1,568 | 1.100 | +13% |
| France | 79,419 | 2,005 | 1.153 | +19% |
| Italy | 77,735 | 1,820 | 1.197 | +23% |
| Spain | 87,340 | 1,838 | 1.211 | **+25%** |

**England is the outlier, not the yardstick.** Every other league sits 12 to 25
percent above it. Pooling without a fitted league term would not shade the
numbers, it would move them a fifth of the way to somewhere else.

Season coverage from the league API is essentially total: 2006/07 to 2025/26,
around 460 to 500 players with fouls each year, and about 750,000 minutes
against a theoretical maximum of 752,400. Seasons before 2006/07 carry minutes
and appearances but no fouls, which is why they are on disk and why they cannot
be used for this.

### The provider offset, measured rather than assumed

> ⚠️ **Superseded 2026-08-24, same day, by the player-level measurement.** The
> table below compares each provider's aggregate over its OWN player set, and
> the sets differ: the league's fouls table omits zero-foul players, whose
> minutes (37,227 in 2023/24 alone) dilute the archive aggregate by about 5%.
> Joined player by player through the identity rules, the ratio is **1.0002
> globally and 0.9997 to 0.9998 in every complete season**, flat across volume
> and position. There is no counting difference to correct; there is a
> zero-truncation rule to remember whenever an aggregate rate is computed from
> the API fouls table. The same study exposed the 2021/22 archive hole above.
> Full working in the modelling log, 2026-08-24, and
> `data/reference/provider_offset.json`.

Roadmap item 9 warns that the league API and the FBref archive count fouls
differently and that the offset must be measured before mixing them. Same
competition, same seasons, England only:

| Season | League API | Archive | Gap |
|---|---|---|---|
| 2017/18 | 0.985 | 0.943 | +4.5% |
| 2019/20 | 1.039 | 0.977 | +6.4% |
| 2021/22 | 0.965 | 0.933 | +3.4% |
| 2023/24 | 1.056 | 1.008 | +4.8% |
| 2024/25 | 1.058 | 1.018 | +4.0% |

**The league API reads about 4.6% higher, every season, never once lower.** The
two track the same year-to-year movement, so this is a definitional difference
between providers rather than an error in either. Anything that mixes them has
to carry this term, and anything that swaps one for the other silently will move
every published number by roughly five percent for no stated reason.

## 📊 The number that decides how leagues can be used

Fouls committed per 90, all seasons:

| | Committed | Drawn |
|---|---|---|
| England | 0.972 | 0.934 |
| Italy | **1.197** | **1.128** |

**Serie A runs 23% higher than the Premier League.** For comparison, England's
own variation across eight seasons runs 0.931 to 1.018, a spread of about 9%.

The league effect is more than twice the season effect. So pooling leagues
naively would overstate every Italian player by roughly a fifth, and pooling them
with a fitted league offset is sound. That is the difference between a mistake
and the model in `18-model-roadmap.md`.
