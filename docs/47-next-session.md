# Prompt for the next session

**Status: Proposed 2026-08-29.** Paste everything below the line into a new
chat. It carries the standing rules, the state of the repo this morning, the
brief that was missed, and every idea raised in the last week that is not yet
built. Written after the slip-card brief was answered with a picture instead
of a build.

---

You are working in `~/Projects/foulgorithm`: a Premier League fouls-prediction
product. Python pipeline (`src/foulgorithm`), append-only picks record
(`data/`), statically exported Next.js site (`site/`), scheduled jobs on GitHub
Actions (`.github/workflows`). Read `docs/README.md` first, then the docs it
marks Decided, especially 38, 41, 45, 46 and 44.

## Standing rules (never drift)

- Oliver pushes; you commit and report "ready to push". Never `git push`.
  Never a `Co-Authored-By` line. No em dashes in any writing.
- Tests before implementation. Every change passes: `make test` (Python;
  `tests/test_matchday.py::TestBuild` is network-flaky between rounds),
  `make js-test`, `next build`, `scripts/audit-ui.sh` (baseline only falls),
  `scripts/check-mobile.sh 390` and `320`, `ruff check` and
  `ruff format --check` (CI runs both).
- `site/app/tokens.css` is the only file allowed raw hex or px. A new colour
  goes through the palette validator. Fonts load via `next/font`.
- **One implementation per role** (`docs/41-primitives.md`, enforced by
  `site/lib/primitives.test.ts`): extend a primitive, never fork it. Pitch,
  house slips, match players table, slip card, standings, game sheet, club
  chip, data table are all registered.
- The record is append-only (`data/predictions`, `data/slates`, `data/picks`,
  `data/graded`): nothing edits or deletes a historical row. A game is scored
  under the contract of its kickoff date (`ensemble.in_era`).
- Every decision gets a doc with a status line before code, and every report
  cites the doc number. Docs are Decided, Proposed or Superseded.
- Oliver's rules: disagree by default and find the weakest point first; no
  glazing; plain English; numbers must be defensible; keep responses short.

## Where things stand (29 August 2026, matchweek 2 in play)

- **Contract, live**: `docs/45-foul-events.md`. Every competitor and the
  house make three slips per game, safe / optimistic / rogue, needing four,
  five and six foul events; layout free inside the count; 3+ only on the
  rogue slip and only for players the house prices at 20/100 or better there;
  a player at most once per slip; house price printed on every slip; one
  foul short is a draw; void below two legs. Gated on kickoff date
  (`ensemble.PRICED_FROM = "2026-08-29"`); Friday 28 August was played and
  settled under the old shapes (`docs/38`). Characters rank legs by edge over
  the house among their likely eleven (house expected minutes >= 60) above a
  shout floor (1+ >= 0.50, 2+ >= 0.25, 3+ >= 0.12), falling back to the
  likely eleven then the pool ranked by own probability, thin records last.
  The house's slips follow recipes (four 1+; a 2+ lead; a 3+ lead or two 2+).
- **Fixture page**: matchup lockup with kit-block badges; the house's three
  slips as `SlipCard`s (`HouseSlips`), recomputed live from pitch swaps
  (`lib/houseslips.ts`, a port of `league.house_slips`); pitch with swaps and
  a one-team phone view; game sheet team tier only; the match players table
  (`MatchPlayers`, `docs/46`): every squad player, real per-90 beside
  expected, actuals once played, all columns sortable, XI mark then bench
  behind "show bench" once confirmed, house tier badges, expanded-row prices,
  phone column chooser; the receipt rail of the eleven's slips; results strip
  when played.
- **League**: table with position, W/D/L, legs, FD, Bold, WB (boldness by
  house price, tiebreak), refreshed at every settle; vidiprinter of settled
  bets; magicIan's genetic algorithm breeds a generation every settle
  (`models/evolve.py`, lineage in `data/state/magician_lineage.jsonl`).
- **Jobs**: lineups watcher reads team sheets from the league's API for any
  fixture kicking off inside three hours, wakes four hours out plus a backbone
  cron every two hours; settle only grades games inside its snapshot window;
  an audit line after every settle says whether a confirmed eleven was
  published before kickoff; cups run on the league's API. GitHub's scheduler
  is unreliable (two hours late, sometimes absent); `docs/43-the-clock.md`
  and `ops/clock/` hold a Cloudflare Worker that presses the dispatch button
  instead, waiting on Oliver's token and account.
- **Data**: English player-match archive 2017 to 14 Sept 2025 (81k rows),
  five other leagues to the same date (404k), our own snapshot-built rows
  from 21 Aug 2026 on. The missing year is the highest-weight data in the
  model (decayed, it outweighs the whole archive). Stathead exports are
  barred by Sports Reference's terms (ML training and substitute databases).
  Sportmonks trial then one paid month is the clean route; a permission email
  to Sports Reference is the free long shot.

## The brief that was missed: three slip-card designs, BUILT

Oliver asked for three revolutionary, artistically focused, realistic,
aesthetic, eye-catching designs for the house's three slips, to be TRIED on
the site, not drawn. What he got was a concept sheet (`docs/slip-concepts.png`)
and the standard card rendered three times. Do it properly:

1. Implement three `SlipCard` variants (a `variant` prop on the existing
   primitive, not new components) and a way to see all three live on a
   fixture page, e.g. a variant switcher on `/fixture/[slug]` behind a query
   or a dev route, so Oliver can compare them in place, both themes, phone
   and desktop.
2. The three starting directions, each rendered with real data in the
   concept sheet: **thermal receipt** (cream thermal paper, feed lines,
   serrated tear edges, dot leaders, barcode as slip id, red RISK stamp on
   the rogue); **boarding pass** (dark ticket with a tear-off stub, legs as
   numbered rows, tier in tall vertical type on the stub with the price,
   punched holes, tier colour band); **bookie's slip** (pale ruled paper,
   selections in blue biro via a handwriting face, printed price box, red
   double-ring stamp: ACCEPTED, then WINNER or VOID once settled). Improve
   on them; they are a floor, not a ceiling.
3. Any new colour or paper tone goes in `tokens.css` and passes the palette
   validator; a handwriting face loads via `next/font`; the audit and mobile
   checks must stay green; the variants must degrade honestly in light mode.
4. Then Oliver picks one, and it becomes the house's card. Consider whether
   the eleven's slips on the rail should follow.

## Everything else raised and not yet done

**Displays (`docs/44`)**
- The house's record: grade the safe/optimistic/rogue SLIPS (the legs are
  already house claims in the ledger; the slips are not scored anywhere),
  per-tier hit rate beside the house's claimed price on Track record, the tier
  hit rates in the house section's note, rogue winners on the vidiprinter.
  Highest value; needs pipeline work.
- Referee strip on the fixture page from `matchday.json` (fouls vs league,
  cards booked, matches).
- Team pages read the matchday sheet: kit block with temper gauge, league
  ranks for fouls committed and won, last-five form.
- Distributions in the open on the match players table (the `Dots`
  primitive per row).
- "We said, it was" across the season on Track record and the homepage.
- Boldness explained: tooltips on the column heads and a glossary paragraph
  from `lib/contract.ts`.

**Pipeline and data**
- The take-ons feature for the drawn market: measured as its real correlate,
  data on disk; gate it on the walk-forward harness; house upgrade if it
  passes, one challenger carries it if ambiguous.
- Gradient boosting as a challenger in the harness.
- The gap year: Sportmonks trial (verify fouls committed AND won per player
  per match for 2025/26 PL), then one paid month to backfill legitimately, or
  the permission email to Sports Reference.
- Settle timing from evidence: Friday's totals posted within 2h05 of kickoff
  against a 3h guard; the latency probe (`jobs/stats_latency.py`,
  `latency.yml`) was to log the weekend; read it, cut `STATS_DELAY` and
  `SETTLE_LAG`, decide per-slot vs per-day settle, delete the temporary
  workflow, re-anchor the weekly reschedule to the matchweek's final whistle,
  consider auto-opening each round after settle so `make gameweek` stops
  being the one manual step.
- The clock: Oliver creates the fine-grained token (Actions read/write, this
  repo only) and a Cloudflare account with no card; deploy per `docs/43`.
- Fixture congestion is measured null (modelling log, 26 Aug); a player-level
  minutes-accumulation version is untested.
- Bump chart of league positions and magicIan's lineage timeline once three
  or four rounds have settled.

**Site**
- Remove the TEMPORARY sample vidiprinter block in `site/app/page.tsx` now
  that real settled lines exist.
- Mobile flow ideas Oliver liked: benches collapsed under the pitch;
  game-sheet tabs per club.
- Cup tie pages: bring them onto the same primitives (house slips, match
  players table) rather than their own components; the parallel cups work
  (`docs/40`) predates both.
- "The five" is eleven now; rename the page and nav item.
- Parked: favourite-saving behind the receipt tear; bet strips as
  scoreboards; the 21 and 22 August pages stay unopenable by agreement.

**Housekeeping**
- `docs/42` is superseded; `docs/41` needs a row for `HouseSlips` variants
  once built; `docs/44` items become Decided as they ship.
- The `cup` job in `lineups.yml` still names an API-Football secret it no
  longer needs.
- Watch the settle log's "confirmed elevens before kickoff" line after every
  matchday; MISSING means the lineups chain drifted again.

Start with the slip-card brief. Report with doc numbers.
