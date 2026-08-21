# Site

**Status: Proposed**

## Stack

Next.js App Router with TypeScript, Tailwind and shadcn/ui, charts with visx or Recharts, motion with framer-motion, deployed on Vercel Hobby. Data comes from Supabase through the JS client with the anon key, protected by row level security.

**Portability constraint**: no Vercel-specific APIs (no `@vercel/kv`, no edge config, no Vercel Analytics). Vercel Hobby forbids commercial use, so the day money enters the picture the site has to move. Keeping it plain Next.js means that move is a redeploy on Cloudflare Pages rather than a rebuild. Recorded in [decisions/ADR-004-hosting-portability.md](decisions/ADR-004-hosting-portability.md).

Static generation wherever possible, with incremental revalidation, so most page views cost nothing and stay fast. Realtime is used only on match days.

## Pages

### Fixtures
The landing page. Upcoming matchweek as cards: teams, kickoff, referee, and the model's expected foul environment for the match with an uncertainty band. Sortable and filterable. Past matchweeks reachable and showing graded results.

### Match detail
The core of the product.

- Player table for each market, ranked, showing P(over the default line) and fair odds.
- **The line explorer**: click a player to expand his full probability distribution as an interactive chart, with a draggable line marker. Drag from 0.5 to 2.5 and the probability and fair odds update live. This is the interaction that makes it feel like a tool rather than a table.
- A "why" panel per player: the handful of features moving his number most, in plain words ("faces a high take-on winger", "referee runs 15% above average", "expected 78 minutes"). Explanations get generated from the model, not written by hand.
- Lineup state banner: predicted, or confirmed with the timestamp.

### Matchday mode
On match days the fixture and match pages subscribe to Supabase Realtime. When the lineup poller writes confirmed lineups, the page updates without a refresh: confirmed starters highlighted, ruled-out players struck through, predictions re-ranked. Countdown to kickoff.

This is the single most impressive thing the site can do and it costs nothing, because Realtime is on the Supabase free tier.

### Track record
Every prediction ever published, graded. Filterable by market, model, date and whether the lineup was confirmed. Headline numbers with confidence intervals, a calibration curve, and a cumulative performance chart.

Nothing gets deleted or hidden. The bad weeks are the point.

### Model arena
The leaderboard from `model_runs`: every algorithm, its calibration, its scores, which one is champion and since when. Publishing our own internal bake-off is unusual and it is the most credible thing on the site.

### Weekly review
The rendered output of the Monday review job. What we got right, what we got wrong, what changed.

### Methodology
One honest page explaining what the model does, what it does not know, and where it has been wrong. Links to the docs.

## Auth

Supabase Auth from the first release, with magic link email sign-in. Nothing is paywalled: accounts exist so users can follow teams or players, save preferences and opt into email alerts.

Building auth now rather than later means the eventual paywall is an RLS policy change plus a membership check, not a re-architecture. That was a deliberate choice made when the access model was decided.

## Design direction

Dark-first, dense but not cluttered, closer to a terminal or a trading interface than to a tipster site. Numbers are the hero. No stock photos of footballers, no green ticks, no hype language, no countdown-to-offer banners.

Every probability displayed alongside its uncertainty. A number without an error bar is a lie we are choosing not to tell.

## Accessibility and performance

Colour never carries meaning alone, contrast meets WCAG AA in both themes, charts are keyboard navigable and have table fallbacks. Core Web Vitals watched from the start, because a chart-heavy page is easy to make slow.

## Responsible gambling

Persistent footer with 18+ and BeGambleAware, an interstitial on first visit, and no language that implies certainty or encourages chasing losses. See [13-legal-and-ethics.md](13-legal-and-ethics.md).
