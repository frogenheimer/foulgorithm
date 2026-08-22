"""Does the favourite effect survive as a feature, fitted on one period and tested on another?

The gradient is real: a heavy favourite's players commit about 0.14 fewer fouls
than their own rate predicts, against a heavy underdog's 0.02. Whether that is
worth shipping is a different question, and the match-level version of this idea
already died on collinearity with the team rates.
"""
import io, math
import numpy as np, pandas as pd
from foulgorithm.store.players import load_player_matches
from foulgorithm.sources import football_data
from foulgorithm.identity.teams import HISTORY_TO_FIXTURE
from foulgorithm.models import player_models as pm
from foulgorithm.backtest import metrics as mx
from foulgorithm.publish.site_export import season_labels

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
m = m.dropna(subset=["kickoff_utc"])
raw = pd.DataFrame({c: 1.0 / m[c] for c in ("B365H", "B365D", "B365A")})
tot = raw.sum(axis=1)
m = m.assign(p_home=raw["B365H"] / tot, p_away=raw["B365A"] / tot).dropna(subset=["p_home"])
m["date"] = m["kickoff_utc"].dt.date

hist["short"] = hist["team"].map(lambda t: HISTORY_TO_FIXTURE.get(t, t))
hist["date"] = hist["kickoff_utc"].dt.date
odds = pd.concat([
    m[["date", "home_team_raw", "p_home"]].rename(columns={"home_team_raw": "short", "p_home": "p_win"}),
    m[["date", "away_team_raw", "p_away"]].rename(columns={"away_team_raw": "short", "p_away": "p_win"}),
], ignore_index=True)
d = hist.merge(odds, on=["date", "short"], how="inner")
d = d[d["minutes"] >= 20]

model = pm.build("valentina", "player_fouls_committed")
LINES = (0.5, 1.5, 2.5)

def run(window_start, window_end):
    ev = d[(d["kickoff_utc"] >= pd.Timestamp(window_start, tz="UTC")) &
           (d["kickoff_utc"] < pd.Timestamp(window_end, tz="UTC"))]
    wk = (ev["kickoff_utc"] - ev["kickoff_utc"].min()).dt.days // 7
    out = []
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
            out.append((r.p_win, base, float(r.fouls_committed)))
    return pd.DataFrame(out, columns=["p_win", "base", "actual"])

fit = run("2018-01-01", "2024-06-01")
test = run("2024-06-01", "2026-09-01")
print(f"fit {len(fit):,}   test {len(test):,}")

# Fitted on ALL history before the test window, not on one recent slice. The
# slope is stable in direction and not in size: -0.105, -0.150, -0.261, -0.130
# across successive two-year windows. Fitting on the strongest of those and
# testing on a weaker one over-corrects by a factor of two, which is exactly
# what the first attempt did.
# Centred on the MEAN win probability, not on 0.5. Centring at 0.5 scales up
# every underdog and down every favourite, and there are far more of the former,
# so it raises the average prediction of a model that already over-predicts.
centre = float(fit["p_win"].mean())
x = (fit["p_win"] - centre).to_numpy()
y = (fit["actual"] / fit["base"]).to_numpy()
slope, intercept = (float(v) for v in np.polyfit(x, y, 1))
print(f"centre = {centre:.3f}   slope = {slope:+.4f}   intercept = {intercept:.4f}")
print(f"  heavy underdog x{intercept + slope*(0.1-centre):.3f}   "
      f"heavy favourite x{intercept + slope*(0.9-centre):.3f}\n")

def score(df, use):
    losses, calib, biases = [], [], []
    for r in df.itertuples():
        mean = r.base * (intercept + slope * (r.p_win - centre)) if use else r.base
        mean = max(mean, 0.02)
        dist = model._single_distribution(mean)
        biases.append(dist.mean() - r.actual)
        for L in LINES:
            losses.append(mx.log_loss_at_line(dist, r.actual, L))
            calib.append((dist.prob_over(L), r.actual > L))
    return np.mean(losses), mx.expected_calibration_error(calib), np.mean(biases)

print(f"{'variant':<28}{'logloss':>10}{'ECE':>9}{'bias':>9}")
print("-" * 56)
for label, use in (("current model", False), ("with game state", True)):
    ll, ece, bias = score(test, use)
    print(f"{label:<28}{ll:>10.4f}{ece:>9.4f}{bias:>+9.4f}")
