"""Does the two-stage minutes model beat averaging?

The existing player harness scores with the minutes a player ACTUALLY played,
deliberately, so it measures the foul model alone. That makes it useless here:
the whole point of a minutes model is what happens before minutes are known.

So this reconstructs the real prediction problem. The source data holds only
appearances, so non-appearances are rebuilt: for each team-match, anyone who
played for that team in the previous 30 days but did not play in this one is
recorded as 0 minutes and 0 fouls. That over-counts, since it sweeps in the
injured, suspended and sold, but it is the population we actually publish on.
"""
import numpy as np, pandas as pd
from foulgorithm.store.players import load_player_matches
from foulgorithm.models import player_models as pm
from foulgorithm.backtest import metrics as mx

d = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)

# Rebuild non-appearances.
played = d[["player", "team", "kickoff_utc"]].copy()
teams = d[["team", "opponent", "kickoff_utc", "known_at", "season"]].drop_duplicates(
    subset=["team", "kickoff_utc"])
pos = d.groupby("player")["position"].last()

rows = []
for t in teams.itertuples():
    recent = played[(played["team"] == t.team)
                    & (played["kickoff_utc"] < t.kickoff_utc)
                    & (played["kickoff_utc"] >= t.kickoff_utc - pd.Timedelta(days=30))]
    squad = set(recent["player"])
    appeared = set(played[(played["team"] == t.team)
                          & (played["kickoff_utc"] == t.kickoff_utc)]["player"])
    for p in squad - appeared:
        rows.append(dict(player=p, team=t.team, opponent=t.opponent, venue="",
                         kickoff_utc=t.kickoff_utc, known_at=t.known_at,
                         season=t.season, position=pos.get(p, ""), minutes=0.0,
                         fouls_committed=0, fouls_drawn=0, yellows=0, reds=0,
                         tackles_won=0, interceptions=0, source="reconstructed"))
absent = pd.DataFrame(rows)
print(f"appearances {len(d):,}   reconstructed non-appearances {len(absent):,}")

full = pd.concat([d, absent], ignore_index=True).sort_values("kickoff_utc").reset_index(drop=True)

# Models never train on reconstructed rows, only get scored on them.
train_all = d
evaluation = full[full["kickoff_utc"] >= pd.Timestamp("2024-01-01", tz="UTC")]
week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
LINES = (0.5, 1.5, 2.5)

model = pm.build("valentina", "player_fouls_committed")
out = {k: {"loss": [], "calib": [], "p0": []} for k in ("average minutes", "two-stage mixture")}

for _, batch in evaluation.groupby(week):
    as_of = batch["kickoff_utc"].min()
    train = train_all[train_all["known_at"] <= as_of]
    if len(train) < 20000:
        continue
    model.fit(train)
    for row in batch.itertuples():
        observed = float(row.fouls_committed)
        rate, _ = model.player_rate(row.player, as_of)
        opp = model.opponent_factor(row.opponent, as_of)

        prof = model.minutes_profile(row.player, as_of)
        mean = model._mean_for(rate, prof.mean_minutes(), opp, 1.0, row.player)
        single = model._single_distribution(mean)
        mixed, _ = model.predict_one(row.player, row.opponent, as_of)

        for name, dist in (("average minutes", single), ("two-stage mixture", mixed)):
            out[name]["p0"].append(dist.pmf(0))
            for line in LINES:
                out[name]["loss"].append(mx.log_loss_at_line(dist, observed, line))
                out[name]["calib"].append((dist.prob_over(line), observed > line))

print(f"\n{'variant':<22}{'n':>9}{'logloss':>10}{'ECE':>9}{'P(0) says':>12}")
print("-" * 62)
actual_zero = (evaluation["fouls_committed"] == 0).mean()
for name, v in out.items():
    print(f"{name:<22}{len(v['loss']):>9,}{np.mean(v['loss']):>10.4f}"
          f"{mx.expected_calibration_error(v['calib']):>9.4f}{np.mean(v['p0']):>12.3f}")
print(f"{'actually zero':<22}{'':>9}{'':>10}{'':>9}{actual_zero:>12.3f}")
