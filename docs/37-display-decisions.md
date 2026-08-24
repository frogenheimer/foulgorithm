# The display decisions: what stayed, what moved, what came back

**Status: Decided 2026-08-24, built the same night.** The display audit
([36](36-display-audit.md)) shipped five changes in one evening and left a
plan behind. Oliver ratified each change individually rather than as a
batch, and two of the calls came out differently once the two pick displays
were untangled from each other. This records the decisions and what was
built on the back of them.

---

## 🎯 The two grids, named once and for all

Most of the confusion in the ratification round came from two grids sharing
one mental slot:

| | The matrix (`FivePicks`) | The ladder (`SlipGrid`, aka "the odds matrix") |
|---|---|---|
| Rows x columns | Players x the five characters | The five characters x five price tiers |
| Shows | The committed slates, the picks the league table scores | Combinations manufactured to reach 2/1 out to 20/1 |
| Ever settled | Yes, graded weekly | Never |

They are different answers to different questions, and they now live on
different pages.

## ✅ Ratified as shipped

- **The league table renders at zeros.** Kept, and the rule is now pinned in
  `site/lib/standings.ts`: zeros are a state, the note is the only thing a
  fresh season changes.
- **The stats sheet stays pinned to the fixture page**, and the standalone
  stats page stays retired. Oliver's words: no point having the page, just
  noise.
- **The crossover cards stay on the homepage.**

## 🚦 What moved, and what came back

- **The matrix moved to The five page.** One matrix per game, kickoff order,
  above the full slates. The fixture page no longer repeats the committed
  picks; the round side by side is The five's job.
- **The ladder came back**, at the foot of each fixture page, below the
  stats. It is still nothing the table scores, and its section says so. Its
  price-with-cost framing is unchanged: never a price without what the
  margin takes.
- **The pitch keeps its swap.** With the ladder back on the page the swap
  interaction has its display target again: change a slot and the ladder is
  rebuilt live from the eleven you chose. The swap state lives in
  `FixtureLive` because the pitch and the ladder sit at opposite ends of a
  server-rendered page; the published-until-touched contract is pinned in
  `site/lib/ladder.ts`.
- **The league table moved to the track record page**, so "how have you
  done" has one home. The five page keeps the slates, the matrix and the
  identities.

## 🎯 One pick source, shrunk to fit

The audit's clean end state was one pick engine. The ladder's return means
the ladder machinery stays, so the end state shrank to: **everything that
scores or advertises traces to the slates**. The homepage crossover now
derives from the committed slates (backing means a character committed to
the leg, once, however many of his three shapes repeat it; pricing is the
house blend from the candidate table), while `fixtureSlips` and
`_slip_at_odds` stay in the payload feeding only the fixture-page ladder
and the pitch rebuild. The card shape did not change, so old and new
recorded cards render alike.

## 🚦 The card diet

A homepage card is now kickoff, teams, expected fouls, the crossover as one
line, one link, and the whole card is the link. The referee, the per-leg
detail and the method sentence are one click in. **Played cards are exempt
for now**: they keep the result, the "we said" comparison and the settled
picks, because a loss must stay as visible as a win and past fixtures have
no page yet to carry that record. The exemption dies when past-fixture
pages exist.

## ⚠️ Deliberately left for later

- **Teams and referees pages**: audited, proposal pending. Nothing deleted.
- ~~Past and live fixtures are not clickable~~ **Built, 25 Aug**: every
  publish archives each fixture's page data (`publish/archive.py`), settle
  marks the legs with outcomes, and played games keep a page with the ladder
  at the top marked came in / no / open. Only pre-kickoff publishes land in
  the archive, mirroring the slates' binding rule. Games from before the
  payload history began have no pre-kickoff snapshot and honestly get no
  page.
- **The fivepicks token debt** (nine undefined `var()` references, one red
  vitest, four UI-audit regressions) belongs to in-flight chart work and was
  deliberately not touched.
