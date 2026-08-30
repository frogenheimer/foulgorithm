# Every model plays every bet: the void rule under the contract, and regrading from the record

**Status: Decided 2026-08-30.** Oliver's instruction: the league table must
show the same number of bets played for every model. The rule that gets there
is my call and is stated here so it can be vetoed in one line.

> 💡 **A void is no longer a way out of a bet.** Under the foul-events
> contract (docs/45) a leg whose player never featured counts as zero foul
> events and the bet keeps its target. The bet is then won, drawn or lost like
> any other, and P is the same for everyone who bet on the game.

---

## 🚦 What went wrong on 29 August

The table published on Sunday 30 August read P15, P14, P13 and P12 across
the eleven models for the same five settled games. Two causes, one of them a
record-integrity fault:

1. **The bot graded bets that were not binding.** Spurs v Newcastle was
   republished by hand at 16:19 UTC (the sheet-verdict fix) for a 16:30
   kickoff, so those were the binding versions. The push landed after the
   bot's 20:24 grade, which graded the 15:29 versions it had. Once the two
   histories merged, the binding bets had legs with no graded outcome and
   the table treated them as unsettled or void. Pax read 12 points when the
   binding record gives 18; Valentina read 14 against a true 10.
2. **Voids removed bets from P.** Docs/42 struck a void leg and settled the
   bet on the rest, and voided the whole bet below two legs. Under docs/45 a
   bet has no fixed leg count, so a struck leg quietly shrinks the target
   and a whole void takes the bet out of P. Dottie's rogue on Spurs voided
   to one leg and she read P14 while the others read P15.

---

## 🎯 The rule

For a bet under the contract (kickoff on or after `PRICED_FROM`):

| Case | Before | Now |
|---|---|---|
| **A leg's player has no graded outcome and the game is completed** | leg struck, target shrinks | leg counts as zero events, target unchanged |
| **A bet drops below two graded legs** | whole bet void, not in P | bet scored on its target like any other |
| **Draw** | exactly one foul short | unchanged |
| **Difference** | landed minus shortfall | the void leg's shortfall is its own line: a 2+ shout that never played is two short |

The reason a void should cost: the pool is built from the likely eleven and
the confirmed sheet reaches everyone (30 August fix). A leg on a player who
then never takes the field is a wrong read of the game, and a wrong read is
what the table is for. Under the old shapes a void was a data gap as often
as a bad pick, so the pre-contract games keep docs/42's rule: a game is
scored under the contract of its kickoff date.

An unsettled leg is still not a miss. Nothing changes while a game is open;
the zero applies only once the fixture is `completed` and the settle window
that covers it is on file.

---

## 🚦 Regrading from the record

Grading now runs from the settled rows already on disk, not only from the
snapshot diff at settle time. `data/settled/player_matches.jsonl` keeps one
row per player per window, and every claim for a completed fixture inside a
window can be graded from those rows at any time. `settle.regrade_from_windows`
does that: append-only, deduplicated on the claim key, and it runs at every
table refresh, so a binding version that arrives after the bot's grade (a
hand publish pushed late, a rebase) is graded at the next publish rather than
sitting ungraded for the season.

Nothing on the record is rewritten. The 15:29 grades stay on file as grades
of claims that were never binding; the join has always taken only the
binding version's claims.

---

## 🧱 Build

- `publish/league.py`: `join_slates` takes the claims' lines and emits a void
  leg on a completed game as a miss with its line's shortfall for priced
  bets; the table no longer skips a priced bet below two legs.
- `jobs/settle.py`: `regrade_from_windows(completed)`, called from
  `player_round._standings` before the table is built.
- Tests: a void leg under the contract scores as zero events; an old-shape
  void still shrinks the target; the regrade grades an ungraded claim from a
  stored window once and only once.
