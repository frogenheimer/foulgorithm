# The contract: three bets per model, per game

**Status: Decided 2026-08-25, Oliver's sign-off in full. Amended 2026-08-28 by [42](42-priced-bets.md): from matchweek 3 the three fixed shapes become three house-priced bands with free layout.** This supersedes
every earlier description of the five's bets, including the round-wide
slates in [36](36-display-audit.md) and [37](37-display-decisions.md). The
system had been building three bets per model per ROUND since the slates
first shipped; the intent was always per GAME, and the sparse side-by-side
displays were the symptom of that gap.

---

## 🎯 What Foulgorithm is

One reader question, answered honestly: **who fouls tonight, and were you
right last time?** The site is a public, tamper-evident record of five
models playing the same betting game on Premier League fouls. Everything on
it is either a bet, the evidence behind a bet, or proof of how past bets
went. Anything else is furniture.

## 🚦 The test

Each of the five models makes **three bets on every game**:

| Bet | Shape |
|---|---|
| The six | 6 players at 1+ fouls (conceded or won) |
| The threes | 3 players at 2+ |
| The mix | 2 at 2+ and 2 at 1+ |

30 bets per model per ten-game week, 150 across the five. Scored like
football: every leg lands is a win (3pts), one miss is a draw (1), more is
a loss (0). Foul difference breaks ties.

**Binding**: a bet's last version published before ITS OWN game's kickoff
is the one that scores. Bets regenerate at T-60 from the confirmed eleven,
so a model only ever bets on players actually starting. **Void backstop**:
if a leg's player still has no graded outcome once the game is complete
(a failed lineup fetch, an abandoned appearance), the leg voids and the bet
settles on its remaining legs. "Open" is never a permanent state.

**Season start: 2026-08-28**, the first round played under this contract.
Everything before stays in the raw record, unscored: the earlier bets were
a different shape, and a table mixing the two would mean nothing.

## ✅ The pages, one question each

- **Home**, "what's on": cards with kickoff, teams, expected fouls, the
  five's crossover, one link. Played cards show the score and whether the
  bets landed.
- **Fixture**, "this game": pitch, head-to-head facts, players, then each
  model's three bets for this game, priced, displayed as slips. On a played
  game the marked bets lead the page. The odds-tier ladder stays for now as
  a pricing feature lower down (review later).
- **The five**, "who is winning the game between the models": the league
  table at the top, then this week's bets game by game.
- **Track record**, "are the probabilities honest": calibration only.

## 🎨 The look

Enterprise-grade calm. Bets render as **slips**, the object a reader
recognises from any sportsbook, never as sparse spreadsheet grids. One
accent, tokens only, losses styled with the same care as wins.

---

## 🚦 Amendment, 2026-08-25: the 6~7

Six generation-2 challengers joined for the 28 Aug round: **Pax**
(Persistence), **Justine** (Jealousy), **Mabel** (Madness), **Dottie**
(Deviance), **Dele** (Delinquency) and **magicIan** (Intelligence, a genetic
algorithm whose dials evolve after every settle, lineage committed
append-only). The five stay on generation-1 selection as the control group;
the challengers bet under bounded rules:

- **Bounded temperament**: preference = own probability plus a temperament
  term clamped to `TEMPERAMENT_SWAY` (8 points). An obvious pick cannot be
  vetoed by a personality.
- **The hot-take floor**: every slip set carries at least one leg where the
  character beats the pack by `HOT_TAKE_MARGIN` (6 points), swapped in only
  when a draft came out all-consensus. A floor, never a cap.

Eleven competitors, 33 bets per game, one league. The character palette was
extended to eleven colours and validated 2026-08-25 (chroma floor, normal
vision ΔE ≥ 15 on adjacent pairs, 3:1 contrast, both themes; CVD pairs in
the 6-8 band rely on the site-wide rule that a swatch never appears without
its name).

---

## 🚦 Amendment, 2026-08-25 (later): selection unifies, the engine is the edge

The generation split as first built made SELECTION the six's edge, which was
the wrong variable: the intent was always engine upgrades. Two changes:

- **Every competitor now bets logic-first**: own probability plus a
  temperament clamped to that character's own sway (`CHARACTER_SWAY`), and
  the hot-take floor applies to all eleven. The sway widths are the
  personality: Tayler 3 points, most 7-10, B-Dog 12, magicIan 2. The old
  pure-temperament formulas made the five rogue; refusing your own best
  numbers under win/draw/loss scoring was points thrown away.
- **Generation now means ENGINE.** The five stay frozen on the 24 Aug
  engine; the six take gated upgrades as they clear their backtests. Both
  cheap candidates are already dead by measurement (big-five pooling gated
  null 24 Aug; count-specific dispersion tried and deleted as noise), so
  the first live candidate is two-stage minutes, built with its gate, never
  rushed.

Rounds also re-key to the league's own gameweeks in an upcoming change; the
table already fills game by game as bets settle.
