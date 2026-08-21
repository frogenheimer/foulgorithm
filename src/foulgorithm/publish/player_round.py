"""Publish player predictions and each character's picks for the next matchday.

Two outputs in one file:
  - the full board, every player in every fixture, both markets
  - five picks per character, chosen in that character's temperament
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from foulgorithm.characters import base as characters
from foulgorithm.models import player_models as pm
from foulgorithm.sources import football_data
from foulgorithm.store.players import load_player_matches

OUTPUT = Path("site/public/data/players.json")

# Below this, the player is mostly the league prior and we say so.
THIN_EVIDENCE = 8.0
# Required edge over fair odds before we publish a price floor. Fair odds are
# break-even, so backing at exactly fair returns nothing in expectation.
EDGE_MARGIN = 0.10
# Each character publishes this many picks per matchday.
PICKS_PER_CHARACTER = 5

# Pinned bands, UK PHIA yardstick. If we write a word it always means this range.
BANDS = [
    (0.90, "Almost certain"),
    (0.80, "Highly likely"),
    (0.55, "Likely"),
    (0.40, "Realistic possibility"),
    (0.25, "Unlikely"),
    (0.10, "Highly unlikely"),
    (0.00, "Remote chance"),
]


def band(p: float) -> str:
    for threshold, word in BANDS:
        if p >= threshold:
            return word
    return "Remote chance"


def squad(history: pd.DataFrame, team: str, as_of, limit: int = 16) -> list[str]:
    """Who is likely to feature: recent appearances, most minutes first.

    A stand-in for a real predicted lineup, which is a separate modelling job.
    """
    recent = history[(history["team"] == team) & (history["known_at"] <= as_of)]
    if recent.empty:
        return []
    cutoff = recent["kickoff_utc"].max() - pd.Timedelta(days=200)
    recent = recent[recent["kickoff_utc"] >= cutoff]
    ranked = (
        recent.groupby("player")["minutes"].agg(["sum", "size"]).sort_values("sum", ascending=False)
    )
    return [p for p, r in ranked.iterrows() if r["size"] >= 2][:limit]


def publish(output: Path = OUTPUT) -> dict:
    history = load_player_matches()
    fixtures = pd.DataFrame(football_data.fetch_fixtures())
    as_of = datetime.now(timezone.utc)

    committed = {c: pm.build(c, "player_fouls_committed") for c in pm.CHARACTER_SETTINGS}
    drawn = {c: pm.build(c, "player_fouls_drawn") for c in pm.CHARACTER_SETTINGS}
    for model in list(committed.values()) + list(drawn.values()):
        model.fit(history)

    house_c, house_d = committed["tayler"], drawn["tayler"]

    board = []
    all_rows: list[dict] = []

    for fx in fixtures.itertuples():
        fixture_block = {
            "key": f"{fx.home_team_raw}-{fx.away_team_raw}",
            "home": fx.home_team_raw,
            "away": fx.away_team_raw,
            "kickoff": fx.kickoff_utc.isoformat(),
            "referee": fx.referee_raw,
            "teams": {},
        }
        for team, opponent in ((fx.home_team_raw, fx.away_team_raw), (fx.away_team_raw, fx.home_team_raw)):
            players = []
            for player in squad(history, team, as_of):
                dist_c, why_c = house_c.predict_one(player, opponent, as_of)
                dist_d, why_d = house_d.predict_one(player, opponent, as_of)
                row = {
                    "player": player,
                    "team": team,
                    "opponent": opponent,
                    "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
                    "kickoff": fx.kickoff_utc.isoformat(),
                    "expectedMinutes": why_c["expectedMinutes"],
                    "effectiveMatches": why_c["effectiveMatches"],
                    "thin": why_c["effectiveMatches"] < THIN_EVIDENCE,
                    "committed": _market_block(dist_c, why_c),
                    "drawn": _market_block(dist_d, why_d),
                }
                players.append(row)
                all_rows.append(row)
            fixture_block["teams"][team] = sorted(
                players, key=lambda r: -r["committed"]["p1plus"]
            )
        board.append(fixture_block)

    picks = [
        _character_picks(cid, history, fixtures, committed[cid], drawn[cid], as_of)
        for cid in pm.CHARACTER_SETTINGS
    ]

    top = sorted(all_rows, key=lambda r: -r["committed"]["p1plus"])[:12]

    payload = {
        "generatedAt": as_of.replace(microsecond=0).isoformat(),
        "trainedOn": {
            "playerMatches": len(history),
            "players": int(history["player"].nunique()),
            "from": history["kickoff_utc"].min().strftime("%b %Y"),
            "to": history["kickoff_utc"].max().strftime("%b %Y"),
        },
        "edgeMargin": EDGE_MARGIN,
        "topFoulers": top,
        "board": board,
        "picks": picks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    return payload


def _market_block(dist, why: dict) -> dict:
    out = {"why": why, "exact0": round(dist.pmf(0), 4)}
    for n in (1, 2, 3):
        p = dist.prob_over(n - 0.5)
        out[f"p{n}plus"] = round(p, 4)
        out[f"fair{n}"] = round(1 / p, 2) if p > 0.001 else None
        out[f"floor{n}"] = round((1 / p) * (1 + EDGE_MARGIN), 2) if p > 0.001 else None
        out[f"band{n}"] = band(p)
    out["outOf100"] = round(dist.prob_over(0.5) * 100)
    return out


def _character_picks(cid, history, fixtures, model_c, model_d, as_of) -> dict:
    """Five picks, chosen the way this character would choose them."""
    c = characters.get(cid)
    settings = pm.CHARACTER_SETTINGS[cid]
    candidates = []

    for fx in fixtures.itertuples():
        for team, opponent in (
            (fx.home_team_raw, fx.away_team_raw),
            (fx.away_team_raw, fx.home_team_raw),
        ):
            for player in squad(history, team, as_of, limit=14):
                for market, model in (("committed", model_c), ("drawn", model_d)):
                    dist, why = model.predict_one(player, opponent, as_of)
                    for line in (0.5, 1.5):
                        p = dist.prob_over(line)
                        if p < 0.15 or p > 0.95:
                            continue
                        candidates.append(
                            {
                                "player": player,
                                "team": team,
                                "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
                                "kickoff": fx.kickoff_utc.isoformat(),
                                "market": market,
                                "line": line,
                                "prob": round(p, 4),
                                "band": band(p),
                                "outOf100": round(p * 100),
                                "fair": round(1 / p, 2),
                                "floor": round((1 / p) * (1 + EDGE_MARGIN), 2),
                                "why": why,
                                "thin": why["effectiveMatches"] < THIN_EVIDENCE,
                            }
                        )

    # Temperament decides the shortlist. Terror wants the safest available;
    # anger wants the boldest it still believes in; the rest sit between.
    if cid == "tayler":
        candidates = [x for x in candidates if not x["thin"]]
        chosen = sorted(candidates, key=lambda x: -x["prob"])
    elif cid == "alan":
        chosen = sorted(candidates, key=lambda x: (abs(x["prob"] - 0.45), -x["prob"]))
    elif cid == "bdog":
        chosen = sorted(candidates, key=lambda x: (-x["thin"], abs(x["prob"] - 0.5)))
    elif cid == "valentina":
        chosen = sorted(candidates, key=lambda x: -x["why"]["opponentFactor"] * x["prob"])
    else:  # lily, drawn to the biggest names and the biggest numbers
        chosen = sorted(candidates, key=lambda x: -x["why"]["ratePer90"] * x["prob"])

    picks, seen = [], set()
    for cand in chosen:
        if cand["player"] in seen:
            continue
        seen.add(cand["player"])
        picks.append(cand)
        if len(picks) == PICKS_PER_CHARACTER:
            break

    combined = 1.0
    for p in picks:
        combined *= p["prob"]

    return {
        "id": c.id,
        "name": c.name,
        "emotion": c.emotion,
        "tagline": c.tagline,
        "settings": settings,
        "picks": picks,
        "combinedProb": round(combined, 4),
        "combinedFair": round(1 / combined, 1) if combined > 0 else None,
        "averageProb": round(sum(p["prob"] for p in picks) / len(picks), 3) if picks else 0,
    }


if __name__ == "__main__":
    result = publish()
    t = result["trainedOn"]
    print(f"Trained on {t['playerMatches']:,} player-matches, {t['players']:,} players "
          f"({t['from']} to {t['to']})\n")
    print("TOP FOULERS THIS ROUND")
    print(f"  {'player':<24}{'fixture':<30}{'mins':>6}{'1+':>7}{'2+':>7}  band")
    for r in result["topFouler" "s"][:10]:
        c = r["committed"]
        print(f"  {r['player']:<24}{r['fixture']:<30}{r['expectedMinutes']:>6.0f}"
              f"{c['p1plus']:>7.0%}{c['p2plus']:>7.0%}  {c['band1']}")
    print("\nCHARACTER PICKS")
    for block in result["picks"]:
        print(f"\n  {block['name']} ({block['emotion']}) — "
              f"avg {block['averageProb']:.0%}, combined {block['combinedFair']}/1")
        for p in block["picks"]:
            verb = "commits" if p["market"] == "committed" else "draws"
            print(f"    {p['player']:<22} {verb} {p['line']:+.1f}".replace("+", "")
                  + f" {int(p['line']+0.5)}+  {p['prob']:>5.0%}  floor {p['floor']}")
