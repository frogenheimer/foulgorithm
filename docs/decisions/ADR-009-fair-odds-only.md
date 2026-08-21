# ADR-009 — Publish fair odds only, capture market prices manually

**Status**: Accepted
**Date**: 2026-08-21

## Decision

The site publishes our own model's probabilities and fair odds. It never publishes bookmaker prices. Market prices are captured manually for the specific lines we track, purely so closing line value becomes measurable over time.

## Context

The original plan assumed an odds API would supply bookmaker prices for player fouls, making systematic value detection possible. Research on 21 August 2026 found that assumption is wrong in two independent ways.

**The Odds API has no player fouls market and no player tackles market for soccer.** The soccer player props it carries are goalscorer, shots, shots on target, assists, player to receive a card and player to receive a red card.

**Its soccer player props come from US bookmakers only**, stated explicitly in their documentation. The UK books that actually price fouls, meaning Sky Bet, Paddy Power, Bet365 and the rest, are not reachable through it for any market we care about.

The free tier is 500 credits a month, and player props must be fetched one event at a time, so a 10-match round costs 10 credits per refresh. That supports a daily snapshot, not line movement tracking.

So there is no free, licensed route to the prices this project was designed to beat. There is probably no paid route either, short of scraping bookmakers directly.

## Options considered

**Scrape bookmakers directly.** Rejected for the public product. It breaches terms of service, needs constant maintenance against anti-bot measures, and republishing licensed odds data on a public site is a separate and worse problem than fetching it privately. If it ever happens for private use, it gets its own ADR.

**Buy a grey-market odds feed.** Rejected. It costs money, which is a hard constraint, and it resells the same scrape with the same licensing problem.

**Use `player_to_receive_card` from US books as a proxy for the whole system.** Rejected as a general answer, since it says nothing about fouls or tackles. Kept as a narrow validation input for the cards market, with the caveat that US prices differ from UK ones.

**Publish fair odds, capture prices by hand.** Chosen.

## Consequences

- **The public product is model probabilities and fair odds.** That is honest, it is entirely ours to publish, and it sidesteps the licensing problem completely.
- **We cannot make systematic value claims**, and we will not. Claiming an edge we cannot measure would be both dishonest and, once money is involved, a regulatory problem. See [../13-legal-and-ethics.md](../13-legal-and-ethics.md).
- **Closing line value becomes a slow, manual measurement** on a small sample of lines rather than an automatic metric across every prediction. It is still the best evidence of edge available, so it is worth the typing.
- **Calibration carries more weight** as the primary success measure, because it is measurable on every prediction without needing a price. Reflected in [../07-backtesting.md](../07-backtesting.md).
- **The match-level market baseline survives.** football-data.co.uk carries full closing odds from 2019/20, so the backtest can still validate its machinery against a real market, just at match level rather than player level.
- The `odds_snapshots` table stays in the schema and stays sparse by design.
