"""Is the favourite effect stable, or did it only exist in the fitting window?"""

import io

import numpy as np
import pandas as pd

from foulgorithm.identity.teams import HISTORY_TO_FIXTURE
from foulgorithm.models import player_models as pm
from foulgorithm.publish.site_export import season_labels
from foulgorithm.sources import football_data
from foulgorithm.store.players import load_player_matches

hist = load_player_matches().sort_values("kickoff_utc").reset_index(drop=True)
frames = []
for label in season_labels(2017):
    try:
        frames.append(pd.read_csv(io.StringIO(football_data.fetch(label).text())))
    except Exception:
        continue
m = pd.concat(frames, ignore_index=True).dropna(subset=["HF"])
m = m.rename(columns={"HomeTeam": "home_team_raw", "AwayTeam": "away_team_raw"})
m["kickoff_utc"] = pd.to_datetime(m["Date"], dayfirst=True, errors="coerce")
m = m.dropna(subset=["kickoff_utc"]).copy()
raw = pd.DataFrame({c: 1.0 / m[c] for c in ("B365H", "B365D", "B365A")})
tot = raw.sum(axis=1)
m = m.assign(p_home=raw["B365H"] / tot, p_away=raw["B365A"] / tot).dropna(subset=["p_home"])
m["date"] = m["kickoff_utc"].dt.date

hist["short"] = hist["team"].map(lambda t: HISTORY_TO_FIXTURE.get(t, t))
hist["date"] = hist["kickoff_utc"].dt.date
odds = pd.concat(
    [
        m[["date", "home_team_raw", "p_home"]].rename(
            columns={"home_team_raw": "short", "p_home": "p_win"}
        ),
        m[["date", "away_team_raw", "p_away"]].rename(
            columns={"away_team_raw": "short", "p_away": "p_win"}
        ),
    ],
    ignore_index=True,
)
d = hist.merge(odds, on=["date", "short"], how="inner")
d = d[d["minutes"] >= 20]

model = pm.build("valentina", "player_fouls_committed")


def slope_in(start, end):
    ev = d[
        (d["kickoff_utc"] >= pd.Timestamp(start, tz="UTC"))
        & (d["kickoff_utc"] < pd.Timestamp(end, tz="UTC"))
    ]
    if ev.empty:
        return None, 0
    wk = (ev["kickoff_utc"] - ev["kickoff_utc"].min()).dt.days // 7
    xs, ys = [], []
    for _, b in ev.groupby(wk):
        a = b["kickoff_utc"].min()
        train = hist[hist["known_at"] <= a]
        if len(train) < 20000:
            continue
        model.fit(train)
        for r in b.itertuples():
            rate, _ = model.player_rate(r.player, a)
            opp = model.opponent_factor(r.opponent, a)
            base = max(rate * (r.minutes / 90.0) * opp, 0.02)
            xs.append(r.p_win - 0.5)
            ys.append(float(r.fouls_committed) / base)
    if len(xs) < 500:
        return None, len(xs)
    return float(np.polyfit(xs, ys, 1)[0]), len(xs)


print(f"{'window':<22}{'n':>9}{'slope':>10}")
print("-" * 42)
for a, b in [
    ("2018-01-01", "2020-01-01"),
    ("2020-01-01", "2022-01-01"),
    ("2022-01-01", "2024-01-01"),
    ("2024-01-01", "2026-09-01"),
]:
    sl, n = slope_in(a, b)
    print(f"{a[:7]} to {b[:7]:<10}{n:>9,}" + (f"{sl:>10.3f}" if sl is not None else f"{'—':>10}"))
