# Risks and open questions

**Status: Living document. Update it when something resolves.**

Written down because the risks that sink projects are the ones nobody wrote down.

## Risks that could end the project

### The market is efficient enough that we have no edge

The honest base case. Bookmakers price player props less carefully than match results, but "less carefully" is not the same as "badly". If a well-built model cannot beat the closing line, there is no value bet to find.

**How we would know**: closing line value on a few hundred graded predictions, or calibration that matches the market's without beating it.
**Response**: say so publicly. The transparency product still has value and the modelling was still worth doing. This outcome is written into [11-roadmap.md](11-roadmap.md) as an acceptable stopping point.

### Single point of failure on player-level data

**The most serious structural risk in the project.** Research on 21 August 2026 found that API-Football is the only free source of current-season per-player fouls that we can use without a known terms-of-service conflict. Every alternative fails on availability, coverage or permission. See [02-data-sources.md](02-data-sources.md).

There is no fallback. If API-Football changes its free tier, restricts seasons or drops a field, player-level modelling stops.

**Mitigation**: cache every response permanently, so what we have already collected survives. Keep the match-level pipeline independent, since football-data.co.uk covers that with no account at all and 26 seasons of history.
**Residual risk**: high and unavoidable. Worth accepting consciously rather than pretending it is diversified.

### The free tier may not cover the seasons we need

**Blocking, and untested.** API-Football's free plan reportedly restricts which seasons are available and no source states which. If the current season is excluded, the free tier is useless and the entire player-level plan needs rethinking.

**Action**: test with a real key before building anything on it. This is the first thing to do, before any code.

### Sources close without warning

The last 12 months demonstrate how fast this happens:

- **FBref**, the backbone of the 2025 version, moved from open to a Cloudflare interactive challenge over 2024 and 2025, and by April 2026 needed a real browser plus a CAPTCHA solver.
- **FBref lost its advanced data entirely** on 20 January 2026 when its provider terminated the agreement and required deletion. Expected goals, progressive passes and the opponent take-on features this project originally planned to use are simply gone.
- **FotMob** formally objected to scraping in January 2026 and had an open-source library remove support.
- **Understat** stopped embedding data in its HTML around December 2025, breaking every tutorial-based scraper.

**Mitigation**: raw responses stored permanently, so a source disappearing does not erase what we already collected.

### The pipeline breaks silently

The single most likely operational failure. A format change, a renamed column, a source returning an empty table. The 2025 version turned every one of these into "multiplier = 1" and nobody noticed.

**Mitigation**: no bare excepts anywhere, freshness checks per source, row count expectations, unresolved identities halting the run, and a daily alert when something looks wrong.

### The project stops being run

A prediction system without a weekly review degrades quietly. Realistically this is how most personal projects end.

**Mitigation**: the review is automated and pushes a summary to Telegram whether or not anyone asks. The manual part is 20 minutes.

## Open questions

### Settlement definitions are unverified

**This blocks any claim of value.** We do not yet know precisely how the bookmakers we care about settle fouls and tackles: which provider they use, and how that provider treats handballs, offsides, advantage situations and tackles that do not win the ball.

A definition mismatch of even a few percent poisons every edge estimate, because the edge itself is a few percent.

**Needed**: confirm the settling provider for at least one major book per market, and check our data against their published figures for a sample of matches.
**Until then**: publish probabilities and fair odds, make no value claims.

### No route to player fouls odds at all, historical or live

Worse than originally assumed, and now verified. The Odds API carries **no player fouls market and no player tackles market for soccer**, and its soccer player props come from US bookmakers only. So there is no free licensed route to the UK prices this project was designed to beat, historically or in real time.

**Consequence**: the market baseline in [07-backtesting.md](07-backtesting.md) cannot be computed at player level, and value claims cannot be made systematically. Recorded in [ADR-009](decisions/ADR-009-fair-odds-only.md).
**Partial substitutes**: football-data.co.uk carries full closing odds from 2019/20 at match level, which validates the machinery on a real market. `player_to_receive_card` exists at US books, which gives the cards market a weak comparator.
**Response**: publish fair odds, capture the handful of lines we track by hand, and lean on calibration as the primary success measure since it needs no price.

### Is expected minutes a separate model or a feature

Currently specified as a separate model feeding the main one. That is cleaner, and it means the minutes model's errors are not visible to the main model, which may hurt calibration. The alternative is jointly modelling minutes and events.

**Decide by**: milestone M3, empirically, in the harness.

### How to handle promoted clubs

Three clubs arrive each August with no top-flight history, or history from years ago. Championship foul rates are not comparable, since refereeing standards and playing styles differ.

**Current plan**: a league-average prior rather than second-tier numbers, with the prior shrinking as top-flight matches accumulate.
**Open**: whether a discounted Championship signal beats a flat prior. Testable once we have a few promoted-club seasons.

### Whether tackles and fouls should be modelled jointly

Tackles attempted is mechanically the strongest predictor of fouls committed. Modelling them jointly could improve both, at the cost of complexity.

**Decide by**: M6, empirically.

## Things we have decided not to worry about

- **Scale.** Roughly 57,000 player-match rows for 5 seasons. Everything fits in memory. Any instinct to reach for distributed tooling is wrong.
- **Model serving latency.** Predictions are precomputed and written to Postgres. Nothing is computed at request time.
- **Real-time in-play data.** An explicit non-goal.

## Regulatory and account risk

- **Publishing picks publicly moves lines.** If the model has edge and the site gains an audience, publishing shortens that edge's life. This is a deliberate trade of edge for audience, made when the project chose to be a public site.
- **Soft bookmakers restrict winning accounts.** Not a risk to the site, but a limit on anyone acting on it. Worth stating plainly on the methodology page.
- **Charging changes the legal picture.** Hosting has to move off Vercel Hobby, and the payment rail question opens. See [13-legal-and-ethics.md](13-legal-and-ethics.md) and [ADR-006](decisions/ADR-006-free-until-proven.md).
