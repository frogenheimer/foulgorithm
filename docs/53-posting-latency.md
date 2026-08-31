# What the league's posting latency actually is

**Status: Decided 2026-08-31.** The delays settle runs on were set from
caution and described as such in their own comments. `latency.yml` measured
them over the 28 to 30 August matchdays. This is what it found and what the
numbers become.

> 💡 **The league posts player stats live, during the match.** Not after the
> whistle, and not in a batch overnight. A game's totals climb from about
> twenty minutes in and are final within ten minutes of full time. That
> makes the three-hour delay too big by about an hour, and it makes the
> guard that delay implements more necessary than it looked.

---

## 📊 The measurements

Baseline of `season_totals()` taken at each run's start, then polled every
ten minutes, counting players whose totals rose. Six runs, six kickoff
slots. "Final" is the last poll at which the count moved.

| Matchday | Kickoff | Totals final | After kickoff |
|---|---|---|---|
| Sat 29 Aug | 11:30 | 13:35 | **2h05** |
| Sat 29 Aug | 14:00 | 15:47 | 1h47 |
| Sat 29 Aug | 16:30 | 18:30 | 2h00 |
| Sun 30 Aug | 13:00 | 15:03 | 2h03 |
| Sun 30 Aug | 15:30 | 17:15 | 1h45 |
| Mon 31 Aug | 19:00 | 20:59 | 1h59 |

Poll granularity is ten minutes, so read every figure as ±10. The worst
observed case is **2h05**, and the true worst could be 2h15.

**The tables move in play.** The 11:30 game on 29 August had 35 players
moved by 12:55 and 71 by 13:25, while its status was still `L`. Appearance
counts rise in play too, which is the part that matters: a snapshot taken
mid-match records a player as having made his appearance with only part of
his fouls posted, the diff looks perfectly valid, and those fouls are lost
for good. The deferral guard is not belt and braces. It is the only thing
standing between us and a quietly wrong record.

**Totals are final at or before the status flips to Complete**, in all six
slots. Monday's lone 19:00 fixture is the cleanest read of the six, with no
other game to confuse the count: the last of its 31 players landed on the
same poll the status went `C`, and the tables then sat still for the ninety
minutes to the end of the run. That is a stronger signal than any clock, and
it is the basis of the follow-up below.

**Late corrections are real and tiny.** Two players moved at 23:31 on 28
August (4h31 after that kickoff) and one at 19:17 on 30 August (3h47
after), though Monday's run polled ninety minutes past its final movement
and saw none. Where we polled late enough, we usually saw one or two. A
correction landing after a snapshot cannot be misattributed by more than a
foul or two, because it arrives in a window where that player's appearances
did not rise, and the exactly-one-appearance rule drops it. Noted, not
chased.

---

## 🎯 The numbers

| Constant | Was | Now | Why |
|---|---|---|---|
| `settle.STATS_DELAY` | 3h | **2h30** | 25 minutes clear of the worst observed posting, 15 clear of the poll granularity's worst case |
| `schedule.SETTLE_LAG` | 3h45 | **3h15** | the same 45-minute margin over the guard it has always carried |

Saturday's grading moves from 21:15 to 20:45 UK, Sunday's from 19:15 to
18:45. Modest on purpose: the two risks are not symmetric. A wake that
fires late costs half an hour; a snapshot taken early destroys a round's
fouls permanently, and a wake that fires *inside* the guard defers the
whole matchday to the Monday backstop.

**`store/players.STATS_DELAY` is untouched at 3h.** One constant was doing
two jobs. The archive loader uses it to stamp `known_at` on historical rows
so a walk-forward backtest cannot see a result before it was knowable, and
that is the worldfootballR archive, a different feed this probe never
measured. The settle guard now owns its own measured constant and the
archive keeps its own unmeasured one, which is the honest split.

---

## ⚠️ The better guard, not built

The clock is the wrong instrument and the evidence says so: totals were
final at or before status `C` in every slot. A guard that defers while any
of today's fixtures is not yet Complete, with a short buffer after the last
one flips, would be both safer than a clock (immune to long stoppages, VAR
delays, a match starting late) and considerably faster: Saturday's last
game completed about 18:20, so a thirty-minute buffer grades at 18:50
instead of 19:45, an hour and a half earlier than today.

It needs a fallback for the status that never flips (abandonment, a feed
stuck on `L`), which is where the clock earns its place as a backstop
rather than the primary. That is a change of mechanism rather than a change
of number, so it is written down here and left for a decision instead of
folded into this one.

---

## 🧱 Build

- `jobs/settle.py`: its own `STATS_DELAY`, 2h30, measured.
- `jobs/schedule.py`: `SETTLE_LAG` 3h15; the settle wakes regenerated.
- Deleted: `.github/workflows/latency.yml`, `jobs/stats_latency.py`, and
  `latency.yml` from the merge-driver test's list of workflows.
- Kept: `data/state/stats_latency.jsonl`, 146 polls. It is the evidence
  behind every number above and it cost a weekend to gather.
