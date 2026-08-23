# Why leagues differ on fouls

**Status: Explored 2026-08-24 on the pooled six-league data. Not acted on.**

England commits 0.972 fouls per 90 and every other league in the set sits 12 to
25 percent above it. That gap is larger than England's own eight-season spread
of about 9 percent, so anything pooling these leagues has to model it. This is
what the data says about where it comes from.

---

## 🎯 It is not that England tackles less

The obvious explanation is style: fewer challenges, fewer fouls. The data
rejects it.

| League | Fouls/90 | Tackles won/90 | Interceptions/90 | **Fouls per tackle** |
|---|---|---|---|---|
| **England** | 0.972 | 0.905 | 0.906 | **1.074** |
| USA | 1.092 | 0.865 | 0.895 | 1.262 |
| Germany | 1.100 | 0.939 | 0.967 | 1.171 |
| France | 1.153 | 0.974 | 0.999 | 1.183 |
| Italy | 1.197 | 0.846 | 0.905 | **1.415** |
| Spain | 1.211 | 0.895 | 0.881 | 1.354 |

**Italy tackles less than England and fouls 23% more.** Tackle rates sit in a
narrow band, 0.846 to 0.974, while fouls per tackle spread from 1.074 to 1.415.

Correlations, and they are the point:

- Across the six leagues, **corr(fouls, tackles won) = −0.135**
- Across England's own seasons, **corr = −0.235**

Both near zero and if anything negative. More tackling does not produce more
fouls, in either direction of comparison. Whatever separates these leagues is
not how much defending happens.

## 🚦 The gap is in every position

| Role | ENG | ESP | FRA | GER | ITA | USA | Rest vs England |
|---|---|---|---|---|---|---|---|
| Defenders | 0.865 | 1.108 | 1.070 | 0.994 | 1.130 | 1.009 | **+23%** |
| Midfielders | 1.253 | 1.534 | 1.445 | 1.397 | 1.497 | 1.380 | +16% |
| Forwards | 1.151 | 1.415 | 1.356 | 1.319 | 1.408 | 1.271 | +18% |

Present everywhere, 16 to 23 percent, largest for defenders. A style difference
would be expected to concentrate in particular roles; a change in what gets
whistled would not.

## ⚠️ What this does and does not establish

**Supported:** the difference is roughly multiplicative and roughly uniform
across positions, and is not explained by the volume of defensive actions.

**The leading hypothesis is officiating interpretation** — the same contact
being called differently — and defenders showing the largest gap is consistent
with more latitude for defensive challenges in England.

**Not established.** This is not a demonstrated cause. We have no referee
identity across leagues, no measure of dribbling volume or pressing intensity,
and no possession data at player-match level. Any of those could carry part of
it. Yellow cards per foul do not separate the leagues cleanly either: France is
lowest at 0.149 while sitting mid-table on fouls, so referees are not simply
uniformly stricter where fouls are higher.

Worth stating plainly because "referees are stricter abroad" is exactly the kind
of explanation that feels settled after one table and has not been tested here.

## ✅ What it means for the model

Directly relevant to roadmap item 8, which pools these leagues.

1. **A single league intercept should be enough.** The gap is close to uniform
   across positions, so a league-by-position interaction is unlikely to earn its
   parameters. Worth testing, not worth assuming.
2. **It should be multiplicative, not additive.** The gap holds proportionally
   across roles with very different base rates.
3. **A player moving leagues should carry his rank, not his rate.** If this is
   interpretation rather than behaviour, a Serie A player's foul count overstates
   what he would concede in England by roughly a fifth, while his standing among
   his peers transfers intact. That is the testable prediction, and the cleanest
   way to check it: find players who moved and see whether rank survives the
   move better than rate does.
