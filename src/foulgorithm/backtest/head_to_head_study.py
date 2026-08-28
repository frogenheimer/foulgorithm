"""Does Valentina's head-to-head method make her better, or only different?

Both are worth knowing. The method exists so she has one, because an opponent
weight of 1.6 is not a way of reading a match. Whether it also improves her is a
separate question and the answer is allowed to be no.
"""

import numpy as np
import pandas as pd

from foulgorithm.backtest import metrics as mx
from foulgorithm.identity.teams import HISTORY_TO_FIXTURE
from foulgorithm.models import player_models as pm
from foulgorithm.publish.site_export import season_labels
from foulgorithm.sources import football_data
from foulgorithm.store.players import load_player_matches

LINES = (0.5, 1.5, 2.5)

hist = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)
frames = []
for label in season_labels(2000):
    try:
        frames.append(pd.DataFrame(football_data.parse(football_data.fetch(label))))
    except Exception:
        continue
matches = pd.concat(frames, ignore_index=True).dropna(subset=["home_fouls"])
matches["known_at"] = pd.to_datetime(matches["known_at"], utc=True)

hist["short"] = hist["team"].map(lambda t: HISTORY_TO_FIXTURE.get(t, t))
hist["oppShort"] = hist["opponent"].map(lambda t: HISTORY_TO_FIXTURE.get(t, t))

ev = hist[hist["kickoff_utc"] >= pd.Timestamp("2023-01-01", tz="UTC")]
wk = (ev["kickoff_utc"] - ev["kickoff_utc"].min()).dt.days // 7

model = pm.build("valentina", "player_fouls_committed")
out = {"without": {"l": [], "c": []}, "with": {"l": [], "c": []}}
factors = []

for _, b in ev.groupby(wk):
    a = b["kickoff_utc"].min()
    train = hist[hist["known_at"] <= a]
    if len(train) < 20000:
        continue
    model.fit(train)
    model.fit_pairings(matches, a)
    for r in b.itertuples():
        rate, _ = model.player_rate(r.player, a)
        opp = model.opponent_factor(r.opponent, a)
        base = max(rate * (r.minutes / 90.0) * opp, 0.02)
        f = model.head_to_head_factor(r.short, r.oppShort)
        factors.append(f)
        observed = float(r.fouls_committed)
        for name, mean in (("without", base), ("with", max(base * f, 0.02))):
            d = model._single_distribution(mean)
            for L in LINES:
                out[name]["l"].append(mx.log_loss_at_line(d, observed, L))
                out[name]["c"].append((d.prob_over(L), observed > L))

factors = np.array(factors)
print(f"n = {len(factors):,} player-matches")
print(
    f"factor range {factors.min():.3f} to {factors.max():.3f}, "
    f"sd {factors.std():.4f}, non-neutral {(factors != 1.0).mean():.0%}\n"
)
print(f"{'variant':<28}{'logloss':>10}{'ECE':>9}")
print("-" * 47)
for name, v in out.items():
    print(
        f"{'Valentina ' + name + ' head-to-head':<28}{np.mean(v['l']):>10.4f}"
        f"{mx.expected_calibration_error(v['c']):>9.4f}"
    )
