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
| **Player fouls, season totals** | Premier League tables | current season only | **yes** |
| Player fouls per match | FBref direct | — | blocked |
| Player fouls | FPL | — | **does not exist** |
| Player events incl. fouls | StatsBomb open data | 2 PL seasons | no |

Two things follow, and they are different problems that get confused:

1. **Volume** is solvable and free. Five more leagues of player-level fouls are
   sitting in the same archive we already use, about 450,000 player-matches
   against the 81,000 we read today.
2. **Recency** is not solvable for free at player level. Everything in that
   archive froze on the same day.

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

### Player fouls, current, at season-total level

The league's own ranked stat tables give fouls and fouls-drawn per player as
**season totals**, live. A single match is recoverable as the difference between
two snapshots, which is what `jobs/settle.py` already does. It covers players our
archive has never seen, Rio Ngumoha included.

Going forward only. It cannot reconstruct 2025-26.

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
