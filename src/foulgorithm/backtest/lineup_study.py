"""How often does our predicted eleven match who actually started?

The proposal is to buy or scrape an expected-lineup feed so picks only cover
starters. Sportmonks quotes about 84% for the Premier League at 34 euros a
month. Worth knowing what we already get for nothing before paying for that.

Our method: rank a club's available players by starts then minutes as of the
match date, take the top eleven. Scored against who actually played 60+ minutes,
which is the practical definition of "started" for a foul market.
"""

import numpy as np
import pandas as pd

from foulgorithm.store.players import load_player_matches

d = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)
d["started"] = d["minutes"] >= 60

ev = d[d["kickoff_utc"] >= pd.Timestamp("2023-08-01", tz="UTC")]
weeks = (ev["kickoff_utc"] - ev["kickoff_utc"].min()).dt.days // 7

hits, totals, per_match = 0, 0, []
for _, batch in ev.groupby(weeks):
    as_of = batch["kickoff_utc"].min()
    past = d[d["known_at"] <= as_of]
    if len(past) < 20000:
        continue
    # Form table as of now: starts and minutes this season so far.
    season_start = as_of - pd.Timedelta(days=330)
    recent = past[past["kickoff_utc"] >= season_start]
    if recent.empty:
        continue
    g = recent.groupby(["team", "player"])
    form = pd.DataFrame({"starts": g["started"].sum(), "minutes": g["minutes"].sum()}).reset_index()

    for team, side in batch.groupby("team"):
        actual = set(side[side["started"]]["player"])
        if len(actual) < 9:
            continue
        pool = form[form["team"] == team].sort_values(["starts", "minutes"], ascending=False)
        predicted = set(pool.head(11)["player"])
        if not predicted:
            continue
        hit = len(predicted & actual)
        hits += hit
        totals += 11
        per_match.append(hit)

per_match = np.array(per_match)
print(f"team-matches scored: {len(per_match):,}\n")
print(f"predicted XI accuracy: {hits / totals:.1%}  ({hits:,} of {totals:,} slots)")
print(f"average correct per XI: {per_match.mean():.1f} of 11")
print()
print(f"{'correct out of 11':<20}{'share':>8}")
print("-" * 30)
for k in range(11, 5, -1):
    print(f"{k:<20}{(per_match == k).mean():>8.1%}")
print(f"{'5 or fewer':<20}{(per_match <= 5).mean():>8.1%}")
