# Idea register

**Status: Living. Every idea raised so far, and where it actually stands.**

Compiled because ideas were accumulating across a dozen documents and two of
them had been discussed and then quietly dropped rather than decided.

Legend: **Built** · **Next** · **Planned** · **Deferred** · **Dropped**

---

## Data

| Idea | Status | Note |
|---|---|---|
| Match history, 26 seasons | **Built** | 9,880 matches, football-data.co.uk |
| Player-match history | **Built** | 81,327 rows, fouls committed and won |
| Live squads | **Built** | FPL API, catches transfers and injuries |
| Confirmed lineups | **Built** | League API, about an hour pre-kickoff |
| Results ingestion | **Built** | Same source, minutes after full time |
| Current-season league leaders | **Built** | The context rail |
| Referee appointments | **Built** | Carried on the fixture list |
| Championship data for promoted clubs | **Deferred** | Raw data is likely one download; the discount factor is the real work |
| Possession, take-ons, progressive carries | **Dropped** | Lived on FBref, deleted in the January 2026 Opta termination |
| Pitch location of fouls | **Dropped** | Needs event data, free only for 2015/16 |
| Bookmaker odds | **Deferred** | No archive exists for fouls or tackles at any price |

## Markets

| Market | Status |
|---|---|
| Match total fouls | **Built**, backtested, champion promoted |
| Player fouls committed | **Built**, backtested, calibration-corrected |
| Player fouls won | **Built**, backtested, calibration-corrected |
| Player cards | **Next.** Registered, data in hand, no model. The only market with real bookmaker odds to check against |
| Player tackles | **Planned.** Registered, data in hand, no model |
| Combination tickets, 4/5/6 fouls | **Built**, with the independence caveat stated |
| Compound fouls-and-cards | **Deferred.** Needs a joint model: multiplying marginals overstates it, which is the expensive direction |
| Team fouls, shots, offsides, corners | **Planned.** Nearly free once the harness exists |

## Models

| Idea | Status | Note |
|---|---|---|
| Shrunken rate baseline | **Built** | |
| Position-aware priors | **Built** | Fixed Alan backing four goalkeepers |
| Time decay | **Built** | 400-day half-life, tuned |
| Referee factor | **Built** | Shrunk, still a confounded ratio |
| Calibration correction | **Built** | Needs re-fitting on held-out seasons |
| Count-specific dispersion | **Next** | Fixes the diagnosed cause rather than the symptom |
| Two-stage minutes | **Next** | Biggest driver, still the crudest part |
| Hierarchical Bayesian | **Planned** | Replaces guessed shrinkage constants with derived ones |
| Joint match model | **Planned** | Makes combination tickets honest |
| Gradient boosting | **Planned** | Challenger, to test whether the hand-specified structure leaves anything |
| Opponent interaction features | **Blocked** | The data was deleted from FBref |
| Ensemble | **Planned** | |

## The five characters

| Idea | Status |
|---|---|
| Five temperaments as real models | **Built** |
| Equal-risk comparison | **Built**, now four odds tiers |
| Season-long replay competition | **Built**, and it found selection bias |
| Character-specific research methodology | **Not done.** See below |
| Characters evolving in character | **Planned**, weekly, logged |

**The gap worth naming.** Each character's *selection* is currently a scoring
formula, not a research method. The suggestion was that Valentina should
actually analyse historical meetings between two clubs against that season's
league average to derive her derby factor, rather than leaning on a generic
opponent term. That is the difference between a personality and a parameter,
and it applies to all five. Nothing has been built for it.

## Site

| Idea | Status |
|---|---|
| Leaderboard, dot arrays, price floors | **Built** |
| Disagreement chart | **Built**, the centrepiece |
| League leaders rail | **Built** |
| Day strip and fixture grid | **Built** |
| Head-to-head comparison | **Built** |
| Filter, search, sort, market tabs | **Built** |
| Chart pack | **Built**, five types, zero client JavaScript |
| Animated favicon | **Built** |
| Calibration page | **Next.** Unblocked now grading exists |
| Track record page | **Next.** Same |
| Model arena page | **Planned** |
| Month calendar view | **Deferred.** Forty cells each showing a number recreates the density problem |
| Theme toggle | **Planned.** System preference only today |
| Odds checker, paste your price | **Planned.** Client-side, free, closes the loop |
| The negative call, do not back under X | **Planned** |

## Infrastructure

| Idea | Status |
|---|---|
| Append-only prediction store | **Built** |
| Grading job | **Built**, nothing settled yet |
| Weekly cron, predict and grade | **Next.** Entirely manual today |
| Freshness monitoring | **Planned** |
| Telegram alerting | **Planned** |
| Supabase database | **Dropped for now.** Files in git give better provenance at this volume |
| Supabase Auth | **Deferred** with the paywall |
| Season rollover | **Planned** |

## Commercial and later

| Idea | Status |
|---|---|
| Charging for access | **Deferred** until the record justifies it |
| Public leaderboard and gamification | **Idea only.** Prizes can make it a regulated product |
| Affiliate links | **Not planned.** Would pull us into CAP Section 16 directly |
| Multi-league expansion | **Deferred.** Architecture supports it, data quality is the constraint |
| Public API | **Idea only** |

---

## The two things that were asked for and never delivered

**1. Character research methodology.** Described above. The characters differ in
parameters but not in *method*, and the original intent was that they should
differ in how they investigate a fixture.

**2. A review of the xItems.** "Expected fouls" is used in several places
meaning slightly different things: the model's mean for a player, the sum across
a starting eleven, and the match-total model's output. They are not the same
quantity and should not share a name. Nothing has been done about it.

## Housekeeping

Sixteen documents still carry "Proposed" for work that shipped weeks ago.
`03-data-model.md` describes a Supabase schema that does not exist and will not;
`08-site.md` describes a site that no longer resembles what is built. That is
exactly the doc rot the repository's own rules warn about, and it needs a
reconciliation pass.
