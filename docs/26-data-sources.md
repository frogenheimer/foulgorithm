# Every source we use

**Status: Living. Update it when a source is added, changes, or dies.**

Four live sources and two frozen archives. All free, none authenticated, and
every one of them has a way of failing that we have already been bitten by.

---

## 🔌 Live, on every matchday

### Premier League API (`footballapi.pulselive.com`)

The one that finishes the lineup problem. Unauthenticated, free, run by the
league.

| What | Where | Notes |
|---|---|---|
| Fixtures, kickoff times, status | `fixtures?comps=1&compSeasons={id}` | **Carries no officials at all**, for played matches as much as future ones |
| Confirmed elevens and formation | `fixtures/{id}` → `teamLists` | Published at **T-60**. Formation arrives as lines of player ids, goalkeeper first |
| Referee | `fixtures/{id}` → `matchOfficials` | Detail only, never the list. Fetched once per completed fixture and cached |
| Match team stats | `stats/match/{id}` | `fk_foul_lost`, `fk_foul_won`, `total_yel_card`. Team level, never per player |
| Season player totals | `stats/ranked/players/{stat}` | `fouls`, `was_fouled`, `appearances`. **Season totals only**, so a single match is the difference between two weekly snapshots |

**Requires `Origin` and `Referer` headers** pointing at premierleague.com or it
refuses. Fixture ids must be sent as integers: JSON parses them as floats and
`128923.0` returns a 400 that reads like a missing fixture.

⚠️ **Terms.** The league restricts commercial use and bars building a competing
database from their content. Fine for a free non-commercial site publishing its
own model output. Must be revisited before any money changes hands.

### Fantasy Premier League API (`fantasy.premierleague.com/api`)

| What | Notes |
|---|---|
| Current squads, all 20 clubs | ~600 players, updated continuously, catches transfers |
| Availability | `status`, `chance_of_playing_next_round`, `news`. Club-sourced injury and suspension |
| Season form | `starts`, `minutes`, `starts_per_90` |

**No predicted lineup.** Every field was checked; nothing is forward-looking.
This is why the predicted eleven leads with whoever started last match instead.

### football-data.co.uk

Plain CSV per division per season, no key.

| What | Notes |
|---|---|
| Match results, fouls, cards, shots, corners | `E0` top flight, `E1` Championship. **Fouls and cards start 2000/01** |
| Referee appointments | On `fixtures.csv`, which the league's own API does not carry |
| Closing bookmaker odds | Bet365, Pinnacle, William Hill and others, back to 2000 |

⚠️ The **current season's file does not exist until the season is under way**,
which is exactly when a promoted club most needs a prior. A season in progress
returns HTTP 300 with an HTML body, which reads like an outage rather than a
season that has not started.

### worldfootballR player data (GitHub release)

`ENG_M_1st_misc_player_advanced_match_stats.csv`, downloaded once and read from
disk forever.

**81,327 player-matches, Aug 2017 to Sep 2025.** One row per player per match:
minutes, fouls committed, fouls drawn, cards, tackles, interceptions.

🛑 **Frozen.** The repository is archived and the file stops in September 2025.
It is the spine of every player market and it does not grow. Current-season
player data comes from the league's ranked tables by subtraction instead.

---

## 🛑 Sources we do not have

Worth listing, because their absence shapes what the model can be.

| What | Why not |
|---|---|
| **Player-level positional or heatmap data** | Lived on FBref and went with the January 2026 Opta termination. Nothing free replaced it. This is what blocks the pitch heatmap idea |
| **Possession, take-ons, progressive carries** | Same termination. Not in the 26 seasons of match files |
| **Championship player data** | FBref advanced stats cover the top five European leagues only. A promoted club has a team record and no player record, at any price |
| **Bookmaker odds for player fouls** | No archive exists anywhere. Checked against a paid API's full market list: `player_to_receive_card`, `player_tackles_over` and `player_shots` all exist; fouls do not. Cards remain the only market where we could ever check ourselves against real prices |
| **Expected lineups** | Sportmonks sells a curated feed at about 84% for €34/month. Our own is 78% and free |

---

## 📊 What each model is trained on

| Model | Trained on |
|---|---|
| Player fouls committed and won | 81,327 player-matches, 2017 to 2025, time-decayed |
| Position priors | The same, grouped by position |
| Calibration correction | Fitted 2022-2024, tested 2024 onward |
| Promoted-club priors | 66 promotions since 2001, match-level, `E0` and `E1` |
| Head-to-head (Valentina only) | 9,120 matches, 428 pairings with 8+ meetings |
| Involvements | Convolution of the two markets, validated on 5,761 player-matches |
| Cards | Fitted on the same player history. Barely beats a base rate |

---

## ⚠️ How each one has actually failed

Not hypothetical. Every row here cost a debugging session.

| Source | Failure |
|---|---|
| Premier League API | Names differ from every other source. "Man United" against "Manchester United" silently disabled the opponent factor for half the league |
| Premier League API | Officials on detail only. Six played matches showed "No referee yet" |
| FPL | Display names against full names. Settlement joined 24 of 1,913 claims |
| football-data | Current season 300s until it starts |
| worldfootballR | Frozen at Sep 2025, so anything current needs the subtraction route |
| All of them | Team names. Four crosswalks exist and a guard test now asserts every club we predict resolves |
