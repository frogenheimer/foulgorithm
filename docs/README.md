# Documentation

These docs are the source of truth for how Foulgorithm works and why. Chat history is not. Code comments are not. If a decision matters beyond the week it was made, it lives here.

## Read in this order

| Doc | What it covers |
|---|---|
| [00-vision.md](00-vision.md) | What we are building, who for, what we deliberately are not building |
| [01-architecture.md](01-architecture.md) | System shape, components, how data flows end to end |
| [02-data-sources.md](02-data-sources.md) | Every source, what it gives us, how we fetch it, how it breaks |
| [03-data-model.md](03-data-model.md) | Database schema and the point-in-time design that prevents leakage |
| [04-identity-resolution.md](04-identity-resolution.md) | Matching teams and players across sources without name-keyed joins |
| [05-markets.md](05-markets.md) | Market definitions, settlement rules, which distribution family fits each |
| [06-modelling.md](06-modelling.md) | Modelling methodology and the model registry contract |
| [07-backtesting.md](07-backtesting.md) | Evaluation protocol, metrics and the anti-leakage rules |
| [08-site.md](08-site.md) | Front end scope, interaction design, auth |
| [09-dev-workflow.md](09-dev-workflow.md) | The development loop and the zero-cost budget |
| [10-weekly-review.md](10-weekly-review.md) | The Monday review runbook, automated and manual parts |
| [11-roadmap.md](11-roadmap.md) | Build order and milestones |
| [12-risks-and-open-questions.md](12-risks-and-open-questions.md) | What could sink this, and what we have not decided yet |
| [13-legal-and-ethics.md](13-legal-and-ethics.md) | Licensing, terms of service, gambling regulation, responsible gambling |
| [16-design-direction.md](16-design-direction.md) | **How the site should look, read and move, with the evidence** |
| [15-next-phase.md](15-next-phase.md) | **The plan to turn this from machinery into a product** |
| [14-extending.md](14-extending.md) | How to add a market, source, model or league without touching shared logic |
| [17-critical-gaps.md](17-critical-gaps.md) | What was missing when the machinery first ran end to end |
| [18-model-roadmap.md](18-model-roadmap.md) | **Every model idea, in build order, with what changed each one** |
| [19-page-structure.md](19-page-structure.md) | What lives on each page and why |
| [20-visual-language.md](20-visual-language.md) | Charts, colour, motion |
| [21-implementation-review.md](21-implementation-review.md) | What was actually built against what was designed |
| [22-design-rebuild.md](22-design-rebuild.md) | The layout as rebuilt |
| [23-idea-register.md](23-idea-register.md) | Ideas with no commitment attached |
| [24-ui-audit.md](24-ui-audit.md) | The interface audit and the rules it produced |
| [25-match-variance.md](25-match-variance.md) | The under-dispersion diagnosis, **and the measurement that retired it** |
| [26-data-sources.md](26-data-sources.md) | What each matchday source gives us |
| [27-how-it-works.md](27-how-it-works.md) | **The model as built, short version and full, and how the five branch off it** |
| [28-foul-data-sources.md](28-foul-data-sources.md) | **Where foul data can actually be obtained. Every figure fetched, not recalled** |
| [29-why-leagues-differ.md](29-why-leagues-differ.md) | Why England fouls least, and why it is not about tackling |
| [30-external-audit-review.md](30-external-audit-review.md) | The two external audits reviewed against the code, with dispositions |
| [31-next-phase-plan.md](31-next-phase-plan.md) | The prove-then-build phase plan that came out of the audit cycle |
| [32-data-upgrade-plan.md](32-data-upgrade-plan.md) | The revision feeding the 2026-08-24 data expansion into the models |
| [33-settle-schedule.md](33-settle-schedule.md) | **Fixing the settle cadence. Every week it does not run is data lost forever** |
| [34-final-plan.md](34-final-plan.md) | **The plan of record: consolidated order and hard release gates. Start here** |
| [35-weekly-updater.md](35-weekly-updater.md) | **One command per gameweek: refresh, settle, predict, verify, commit, push** |
| [36-display-audit.md](36-display-audit.md) | The display audit: one set of picks, shown three ways |
| [37-display-decisions.md](37-display-decisions.md) | The ratification round: what stayed, what moved, what came back |
| [38-the-contract.md](38-the-contract.md) | **Three bets per model per game. The plan of record; supersedes 36 and 37 on the bets** |
| [39-instrument-grade.md](39-instrument-grade.md) | **The visual redesign: dark-first modules, the chart vocabulary, the temper-ring badges** |
| [44-displays.md](44-displays.md) | **Six displays that are lacking or under-used, planned and ordered** |
| [43-the-clock.md](43-the-clock.md) | **A scheduler that fires on time: a Cloudflare Worker presses GitHub's button. Setup steps and cost guards** |
| [42-priced-bets.md](42-priced-bets.md) | **The contract amended: three bets per game at three house-priced bands, layout free, from matchweek 3** |
| [41-primitives.md](41-primitives.md) | **What already exists. Read before writing a component, a table or a pitch** |
| [40-the-cups.md](40-the-cups.md) | **Both domestic cups, the Championship, and why those ties get a match total and never a player pick** |
| [glossary.md](glossary.md) | Terms, especially the ambiguous ones |
| [ideas.md](ideas.md) | Ideas not committed to. Nothing here is being built |
| [modelling-log.md](modelling-log.md) | **Append-only record of every modelling decision, experiment and result** |

## Audit responses

External audits and our replies live in [audit-responses/](audit-responses/).
Start with [the 2026-08-24 addendum](audit-responses/2026-08-24-data-addendum.md),
which retires one of the blockers the earlier replies were written against.

## Decision records

Numbered ADRs live in [decisions/](decisions/). One decision per file. They are immutable once merged: to change a decision, write a new ADR that supersedes the old one and update the old one's status line.

## Keeping these honest

A doc that describes something we did not build is worse than no doc. Every doc carries a status line at the top:

- **Decided** means we have committed and the code should match.
- **Proposed** means this is the current plan but nothing is built.
- **Superseded** means read the ADR that replaced it.
