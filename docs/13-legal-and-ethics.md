# Legal, ethics and responsible gambling

**Status: Decided, on research verified 21 August 2026. Not legal advice. Get a professional opinion before charging or before adding affiliate links.**

## Gambling licensing: we do not need a licence

Publishing predictions is not a licensable activity. The Gambling Commission says so directly in its betting guidance:

> the Commission does not consider that merely placing advertisements about where to place bets... is sufficient to fall within the definition. In contrast, the offer of tipster services, whereby the tipster places bets on behalf of third parties in return for payment or commission would... fall within the definition

The statutory basis is section 5 of the Gambling Act 2005, and operating unlicensed is an offence under section 33.

**The test is whether we touch stakes.** Four questions, and the answer to all four must stay no:

1. Do we place bets for anyone?
2. Are we party to anyone's betting contract?
3. Do we match users' bets against each other?
4. Do we take a position on any outcome?

Charging a subscription does not change this. Publishing tips for money is still publishing.

## The rules that do apply, and how they change by phase

This is the part that matters, because the obligations shift sharply depending on how the site is funded.

| Phase | What binds us |
|---|---|
| **Free, no affiliate links** (where we are) | CAP rule 1.3, social responsibility. Section 16 is not directly binding, but the ASA imports its principles when judging tipster content |
| **Affiliate links added** | We become a third party acting on an advertiser's behalf, so **CAP Section 16 binds directly**. Plus "Ad" labelling duties |
| **Charging for access** | Consumer law activates: Consumer Rights Act 2015, the 2013 cancellation regulations, and the DMCC Act 2024 misleading-practice regime |

Our own site content counts as advertising once it promotes a paid product. Non-paid-for space under our control is in the CAP Code's scope, so a pricing page or a track record sitting next to a signup button is an ad.

## The proofing requirement

CAP's guidance on betting tipster services applies to football, not only racing, and it is specific:

- **Lodge predictions with a demonstrably independent third party before the events take place.** The guidance names "a well known and reputable firm of accountants or solicitors".
- **Track record claims must state the period and the total stakes** needed to place the bets.
- Claims must be based on starting prices, or state and evidence the basis of other prices.
- The odds must have been available long enough for members to actually get on.
- **Do not cherry-pick periods.**

Our design already does most of this by accident. Predictions are published before kickoff, timestamped, graded afterwards and never deleted. That is self-proofing rather than independent proofing, which is enough while the site is free and makes no profit claims.

**It stops being enough the moment we charge and quote a strike rate.** At that point either we get independent proofing, or we make no performance claims in marketing at all.

## What the ASA has actually punished

Every upheld tipster ruling found turned on the same handful of things:

- Profit claims that could not be substantiated ("£89,270 profit in 5 months", upheld because 95% of the selected bets had starting prices materially worse than quoted).
- Cherry-picked periods, and omitting stakes and starting bank.
- Framing tips as income or financial security ("Best second source of income I've ever had").
- Content not being obviously identifiable as advertising.
- Featuring a promoter who was or appeared under 25.

**The single highest-risk thing we could publish is a profit claim we cannot independently proof.** So we do not publish one.

Note also that the under-25 rule is about who appears in an advert, not about who sees it. It is easy to get that backwards.

## If we ever charge

Charging leaves licensing untouched and activates consumer law hard:

- **Consumer Rights Act 2015 section 50**: pre-contract statements the consumer relied on **become contract terms**. An advertised strike rate or return stops being marketing and becomes a promise we owe.
- **Consumer Contracts Regulations 2013**: a 14-day cancellation right applies, because a tips subscription is not a gambling contract and so is not excluded. That window extends to 12 months if pre-contract information duties are breached. Killing the 14-day right early requires express consent plus explicit acknowledgement before first delivery.
- **DMCC Act 2024**, in force 6 April 2025: misleading actions and omissions, with CMA fines up to 10% of global turnover. It revoked the older 2008 consumer protection regulations, so those should not be cited for anything recent. Schedule 20 bans undisclosed paid editorial and fake or incentivised reviews outright.
- Subscription-specific rules (auto-renewal reminders, cooling-off, easy exit) are expected in spring 2027.

The practical consequence: **if we charge, marketing states no performance figures at all**, or we accept that each one is a contractual term we must be able to prove.

## If we ever add affiliate links

- CAP Section 16 binds directly, as a secondary advertiser, meaning all of it and not just the disclosure rules.
- Content must be labelled **"Ad"**, upfront and prominent, before anyone clicks. "Sponsored", "Spon", "aff" and "affiliate" are all explicitly insufficient.
- The bookmaker carries regulatory responsibility for our conduct under the licence conditions, so they will impose contractual compliance terms and terminate quickly on breach.

None of this is planned. It is written down so that adding one affiliate link is recognised as a regulatory decision rather than a small commercial one.

## Data licensing

The split that matters is private modelling use versus republication.

| Source | Private use | Republication |
|---|---|---|
| football-data.co.uk | Fine | Purpose restriction: "made available for the purposes of league match prediction only". No formal licence. Unresolved for commercial use |
| API-Football | Fine within tier limits | Check terms before republishing raw data |
| Bookmaker odds | Grey | **Never.** Commercially licensed data |
| FBref, FotMob | Not used. See [02-data-sources.md](02-data-sources.md) | n/a |

**We publish our own model's numbers.** Fair odds are derived from our probabilities, not from anyone's prices. See [ADR-009](decisions/ADR-009-fair-odds-only.md).

FotMob deserves a specific note: their endpoints work and are easy, and a FotMob employee formally objected to scraping in January 2026 and had an open-source library remove support. We do not use sources whose owners have said no.

## Responsible gambling

This project models a gambling market, which carries an obligation not to make gambling harm more likely.

Commitments:

- Probabilities and uncertainty, never tips, locks or confidence language.
- No staking advice, unit sizes or bankroll strategy on the public site.
- No performance figure without its sample size and confidence interval.
- Losing periods shown as prominently as winning ones.
- Never framing this as income, investment or financial security. That framing is both a CAP breach and the thing that does real harm.
- 18+ signposting and safer gambling links, despite no CAP rule strictly requiring them of a non-operator. It is right, and it becomes contractually required the moment any commercial relationship exists.

**Support signposting**: National Gambling Helpline 0808 8020 133 (operated by GamCare), gamcare.org.uk, and GamStop self-exclusion at gamstop.co.uk.

⚠️ **Do not hard-code BeGambleAware.org into templates without checking it first.** GambleAware's prevention work has been transferring to government, and reports suggest the charity winds down. Put safer-gambling links in one config value so a dead link is a one-line fix rather than a site-wide edit.

## Honesty commitments

The project's only real asset is being trustworthy about its own performance.

- Every published prediction is graded and retained, including the wrong ones.
- No prediction is edited or deleted after the fact.
- Model changes are dated and visible, so a step change in results can be attributed.
- Metrics are reported with confidence intervals and sample sizes.
- Where we do not know something, the site says so.
