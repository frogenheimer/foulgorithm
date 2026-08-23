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
