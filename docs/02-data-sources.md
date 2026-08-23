# Data sources

**Status: Decided, on evidence verified 21 August 2026.**

Every claim below carries a verification date. These facts rot fast, so re-check before relying on any of them. The verification log is at the bottom.

## Principles

1. **Fetch once, parse many.** Every response is written to `data/raw/` before parsing. Re-running a parser never re-hits the network.
2. **No source is load-bearing alone.** Free access ends without notice, and in the last 12 months it has, repeatedly.
3. **Fail loudly.** A source returning something unexpected raises. It never degrades into a default.
4. **Respect the source.** Rate limits honoured, real user agent with a contact address, nothing behind a login, and no source whose owner has actively objected to being scraped.

## The finding that shapes everything

> ⚠️ **Superseded in part, 2026-08-24.** This section says API-Football is the
> only usable free source of per-player fouls. That was wrong, and the source
> that disproves it is one this project already calls: **the Premier League's
> own API returns per-player foul totals for every season back to 2006/07**,
> free, no key, no block. Twenty seasons, around 470 players each, with minutes
> so everything can be a rate. See `28-foul-data-sources.md`, which supersedes
> the table below.
>
> The distinction the original claim missed is granularity, not permission.
> API-Football gives fouls PER MATCH. The league gives SEASON TOTALS, and a
> single match is recoverable from them only by differencing snapshots taken
> either side of it, which works going forward and cannot be done backwards.
> Both statements can be true and only one was written down.

**API-Football is the only free source of current-season per-player fouls that we can use without a known terms-of-service conflict.** The alternatives each fail on one of availability, coverage or permission:

| Source | Per-player fouls | Free | Usable | Why not |
|---|---|---|---|---|
| **Premier League API** | **Yes, season totals, 20 seasons** | **Yes** | **Yes** | Missing from this table entirely. In use for settlement already |
| **API-Football** | **Yes, per match** | **Yes** | Account suspended | Still the only per-MATCH route |
| football-data.co.uk | No, team level | Yes | Yes | Match level only, but excellent for what it does |
| FBref | Unverified since Jan 2026 | Yes | **No** | Cloudflare interactive challenge, and its Opta data was deleted |
| FotMob | Yes | Yes | **No** | FotMob formally objected to scraping in Jan 2026 and got a library to remove support |
| Understat | **No** | Yes | n/a | Has no fouls, tackles or duels at all |
| football-data.org | No, team level | Yes | Partly | Player data is bookings only, no fouls |
| StatsBomb open data | Yes | Yes | Partly | Premier League stops at 2015/16 |
| WhoScored, Sofascore | Yes | Yes | **No** | Cloudflare and Varnish blocks, unclear permission |

## API-Football (api-sports.io)

**Role: the backbone.** Fixtures, results, lineups and per-player match statistics.

Verified response schema from `fixtures/players`:

```
fouls:   { drawn, committed }
tackles: { total, blocks, interceptions }
cards:   { yellow, yellowred, red }
duels:   { total, won }
```

That covers all three launch markets directly. Premier League is league id 39.

**Free tier: 100 requests per day, 10 per minute, reset at 00:00 UTC with no rollover.**

That budget is workable for live operation and tight for backfill:

| Activity | Cost |
|---|---|
| One matchweek of fixtures | 1 request |
| Lineups for a 10-match round | 10 requests |
| Player stats for a 10-match round | 10 requests |
| **Weekly operating total** | **roughly 25 requests** |
| Backfilling one full season | roughly 380 requests, so 4 days |

Backfill is therefore a slow background activity measured in days, not a one-off import. Plan for it and cache permanently, because a settled match never needs fetching twice.

**Lineups appear 20 to 40 minutes before kickoff** where the competition supports it. Check the `coverage` field on `/leagues` rather than assuming. This is later than the "about an hour" the earlier plan assumed, which tightens the matchday polling window.

⚠️ **Unverified and important**: the free plan reportedly restricts which seasons are available, and no source states which. If the current season is excluded, the free tier is useless to us. **Test this with a real key before building anything on it.** The `/status` endpoint returns plan and remaining quota and is not Cloudflare-blocked.

## football-data.co.uk

**Role: the backtest spine.** Built first, because it needs no account, no key and no scraping.

Verified live on 21 August 2026, updated that morning. Free, updated Sunday and Wednesday nights.

**Coverage is better than expected:**

| What | Detail |
|---|---|
| Fouls committed | `HF`, `AF` |
| Cards | `HY`, `AY`, `HR`, `AR` |
| Referee | `Referee` |
| Shots, corners | `HS`, `AS`, `HST`, `AST`, `HC`, `AC` |
| Seasons with fouls | **2000/01 onward, 26 completed seasons** |
| Closing odds, full suite | **2019/20 onward, 7 completed seasons** |

Closing odds from 2019/20 include Bet365, Pinnacle, market maximum and market average for 1X2, over/under 2.5 and Asian handicap. That gives the backtest a genuine market baseline at match level, which is far more than expected.

**Three traps, all verified:**

1. **A missing season file returns HTTP 300, not 404**, with an HTML body. A parser checking only `response.ok` will happily ingest HTML as CSV. Check `status_code == 200` **and** the content type.
2. **New `HxG` and `AxG` columns appeared in 2026/27**, inserted between `Referee` and `HS`, and undocumented in the notes file. **Parse by column name, never by index.**
3. **Cards exclude the first yellow when a second converts to a red**, in English and Scottish data. Relevant to the cards market.

**Terms**: no formal licence. The only statement is that data is "made available for the purposes of league match prediction only". That is a purpose restriction rather than a permissive licence, and upstream rights sit with third parties. Fine for what we are doing. Unresolved for a commercial phase, recorded in [12-risks-and-open-questions.md](12-risks-and-open-questions.md).

## FBref: no longer usable

The 2025 pipeline was built on FBref. That path is closed, for two independent reasons.

**Blocked.** Verified 21 August 2026: HTTP 403 with a Cloudflare `cType: 'interactive'` challenge on every path, including `robots.txt`. A real browser user agent does not help. Stated rate limit is 10 requests per minute with bans of up to a day, but the rate limit is no longer the binding constraint because the first request is rejected outright.

**Gutted.** On 20 January 2026 FBref's advanced data provider terminated its agreement and required deletion. Sports Reference published this and removed the data. Expected goals, progressive passes and the rest of the Opta-derived metrics are gone. The depth features this project originally planned to take from FBref, particularly take-ons attempted against, are among the deleted set.

**Terms** explicitly name scrapers, competing databases and AI training. There is no API, and custom data requests start at $5,000.

**Decision**: FBref is not a source for this project. Not as a backbone, not as enrichment. If per-player fouls turn out to remain in its basic data and access becomes possible again, that gets revisited in an ADR rather than assumed.

## FotMob: technically easy, deliberately not used

FotMob's undocumented JSON endpoints return per-player fouls committed and drawn with no authentication, and they responded normally when tested.

**We are not using it.** In January 2026 a FotMob employee formally stated that scraping their pages or API endpoints is not permitted, asked an open-source library to remove support, and the maintainer complied. Their `robots.txt` disallows the API path. The data carries Opta identifiers, which is why they defend it.

This is an active, enforced objection rather than a grey area. Using it would mean building on something the owner has explicitly said no to.

## Referee appointments

Appointments publish midweek and the referee is one of the strongest match-level features. A light weekly scrape of the official appointments listing, with `known_at` set to publication time rather than match date.

API-Football carries referee on fixtures as a fallback, though often only close to the match.

## Odds: a much harder problem than assumed

**The Odds API does not offer player fouls or player tackles for soccer.** Verified 21 August 2026. The soccer player prop markets it does carry are goalscorer, shots, shots on target, assists, `player_to_receive_card` and `player_to_receive_red_card`.

**Worse, its soccer player props come from US bookmakers only**, stated explicitly in their documentation. Sky Bet, Paddy Power and the other UK books that actually price fouls are not reachable through it, for any market we care about.

**Free tier is 500 credits per month.** Player props cost markets × regions per event and must be fetched one event at a time, so a 10-match round costs 10 credits per refresh. That is roughly 50 refreshes a month: a daily snapshot, not line movement tracking.

**What this means:**

- Systematic odds comparison for fouls is **not possible for free**, and probably not possible at any price without direct scraping.
- Cards are partially addressable, since `player_to_receive_card` exists, at US prices rather than UK ones.
- Manual entry is the only route to real UK fouls prices.

The consequence is recorded in [ADR-009](decisions/ADR-009-fair-odds-only.md): we publish fair odds from our own model, we capture prices manually for the specific lines we track so closing line value becomes measurable eventually, and we make no systematic value claims we cannot support.

## Adapter contract

```python
def fetch(self, **params) -> RawResponse       # bytes plus metadata, written to data/raw/
def parse(self, raw: RawResponse) -> list[Row] # typed rows, no network access
def known_at(self, row) -> datetime            # when this fact became public
```

Splitting fetch from parse is what makes offline development and replayable parser fixes possible. Every adapter documents its `known_at` rule in its docstring and errs later rather than earlier.

## Verification log

| Date | Finding |
|---|---|
| 2026-08-21 | API-Football free tier: 100/day, 10/min. Per-player fouls, tackles and cards confirmed in schema. Lineups 20 to 40 min pre-kickoff. Season restriction on free plan **unverified** |
| 2026-08-21 | football-data.co.uk live and updated. Fouls from 2000/01. Full closing odds from 2019/20. 2026/27 E0 file not yet created, returns HTTP 300 |
| 2026-08-21 | FBref returns 403 Cloudflare interactive challenge on all paths. Opta advanced data deleted 20 Jan 2026 |
| 2026-08-21 | The Odds API has no soccer player fouls or tackles market. Soccer player props are US bookmakers only |
| 2026-08-21 | FotMob endpoints work without auth, but scraping was formally objected to in Jan 2026 |
| 2026-08-21 | Understat confirmed to carry no fouls, tackles or duels |
