# Ideas

Things worth doing that we have **not** committed to. Nothing here is on the roadmap. Nothing here is being built.

Append new ideas at the top with a date. When an idea gets picked up it moves to [11-roadmap.md](11-roadmap.md) and the entry here is marked promoted rather than deleted, so the reasoning survives. When an idea is rejected, say why and leave it, because the same idea will occur to us again in six months.

---

## 2026-08-21 — Public leaderboard, points and a levelling game

**The idea.** Open the competition beyond the five characters. Any user can make predictions, earn points for accuracy, climb a leaderboard, level up, and win weekly rounds. The five emotions become the house players who seed the board rather than the whole product.

**Why it is interesting.**

- **It is a flywheel.** People come back weekly to defend a rank, which is a far stronger retention loop than checking a tips page. Every returning user also generates a public prediction, which makes the site's core content free to produce.
- **It proves the model in public.** If Alan and Tayler sit mid-table against real humans, that is more convincing than any calibration chart. If they dominate, that is the marketing.
- **It is a safer sell, and Oliver is right about that.** Selling access to a prediction game is not selling betting advice. It sidesteps the CAP tipster proofing requirements, which demand predictions be lodged with an independent third party before events, and it sidesteps the Consumer Rights Act problem where an advertised strike rate becomes a contractual promise. See [13-legal-and-ethics.md](13-legal-and-ethics.md).
- **It sits between markets.** Someone who would never place a bet will still play a free prediction game, which widens the audience well past the betting-curious.

**The two risks that would need resolving first.**

1. **Prizes can turn this into a regulated product.** A free-to-enter competition with a genuine skill element sits outside the Gambling Act. Charge for entry and award prizes on an uncertain event and it can become a lottery, or betting. The line is real and it is not intuitive. Any prize element needs a proper opinion before launch, not after.

2. **Gamifying a gambling-adjacent product is exactly what regulators are looking at.** Points, streaks, levels and weekly rounds are engagement mechanics, and engagement mechanics attached to gambling content are under active scrutiny. A streak that punishes a user for not predicting is the kind of thing that reads badly in a complaint. Designing this well means the game rewards *accuracy and honesty*, never volume or frequency.

**What it would need.** Supabase Auth already ships, so accounts exist. It would need a predictions table for users, a scoring job that runs alongside the existing weekly grading, and the leaderboard itself. The scoring should use a proper scoring rule rather than raw hit rate, for the same reason the characters are normalised: rewarding raw hit rate rewards timid predictions and teaches users the wrong thing.

**Status.** Idea only. Revisit once the characters have a real track record, because a leaderboard with nothing to compare against is an empty room.
