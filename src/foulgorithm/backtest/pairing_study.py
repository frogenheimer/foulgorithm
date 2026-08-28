"""Does WHO a player is up against matter, beyond which team he is up against?

The opponent factor already knows how many fouls a club draws out of teams. The
pairing question is different and narrower: does facing one exceptional
foul-winner move a defender's fouls beyond what his club's average implies?

If it does not, "two midfielders who both foul a lot" is a nice thing to look at
and not a thing that predicts anything, and it should be presented as the
former.
"""

import numpy as np
import pandas as pd

from foulgorithm.models import player_models as pm
from foulgorithm.store.players import load_player_matches

h = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)

# Who actually featured for each side in each match, so "the opponent's best
# foul-winner" means someone who was on the pitch.
h["match"] = (
    h["kickoff_utc"].astype(str)
    + "|"
    + h[["team", "opponent"]].min(axis=1)
    + "|"
    + h[["team", "opponent"]].max(axis=1)
)

model = pm.build("valentina", "player_fouls_committed")
ev = h[(h["kickoff_utc"] >= pd.Timestamp("2024-01-01", tz="UTC")) & (h["minutes"] >= 60)]
wk = (ev["kickoff_utc"] - ev["kickoff_utc"].min()).dt.days // 7

rows = []
cache = {}
for _, b in ev.groupby(wk):
    a = b["kickoff_utc"].min()
    train = h[h["known_at"] <= a]
    if len(train) < 20000:
        continue
    model.fit(train)

    month = (a.year, a.month)
    if month != cache.get("month"):
        g = train.groupby("player")
        nineties = g["minutes"].sum() / 90.0
        cache["month"] = month
        cache["drawn"] = (g["fouls_drawn"].sum() / nineties)[nineties >= 5]
    drawn = cache["drawn"]

    by_match_team = b.groupby(["match", "team"])["player"].apply(list).to_dict()

    for r in b.itertuples():
        opp_players = by_match_team.get((r.match, r.opponent), [])
        rates = [drawn[p] for p in opp_players if p in drawn]
        if len(rates) < 5:
            continue
        rate, _ = model.player_rate(r.player, a)
        opp = model.opponent_factor(r.opponent, a)
        pred = max(rate * (r.minutes / 90.0) * opp, 0.02)
        rows.append((max(rates), float(np.mean(rates)), float(r.fouls_committed) - pred, pred))

d = pd.DataFrame(rows, columns=["best_winner", "mean_winner", "residual", "predicted"])
print(f"n = {len(d):,} player-matches with a known opposing eleven\n")
print(
    f"correlation, opponent's BEST foul-winner vs residual : {d['best_winner'].corr(d['residual']):+.4f}"
)
print(
    f"correlation, opponent's MEAN foul-winner vs residual : {d['mean_winner'].corr(d['residual']):+.4f}"
)
print()
print(f"{'opponent best winner':<24}{'n':>7}{'predicted':>11}{'actual':>9}{'residual':>10}")
print("-" * 62)
d["bucket"] = pd.qcut(d["best_winner"], 5)
for b_, g_ in d.groupby("bucket", observed=True):
    print(
        f"{str(b_):<24}{len(g_):>7,}{g_['predicted'].mean():>11.3f}"
        f"{(g_['predicted'] + g_['residual']).mean():>9.3f}{g_['residual'].mean():>+10.3f}"
    )
