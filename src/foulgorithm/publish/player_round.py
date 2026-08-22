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

    candidates = _candidate_table(history, fixtures, committed, drawn, as_of)
    picks = [_character_picks(cid, candidates) for cid in pm.CHARACTER_SETTINGS]

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


def _candidate_table(history, fixtures, committed, drawn, as_of) -> list[dict]:
    """Every candidate bet, with EVERY character's probability attached.

    Computed once. Selection then reads from it, which is what makes
    "how far is this character from the pack" cheap to ask.
    """
    rows = []
    for fx in fixtures.itertuples():
        for team, opponent in (
            (fx.home_team_raw, fx.away_team_raw),
            (fx.away_team_raw, fx.home_team_raw),
        ):
            for player in squad(history, team, as_of, limit=14):
                for market, models in (("committed", committed), ("drawn", drawn)):
                    dists = {}
                    whys = {}
                    for cid, model in models.items():
                        dists[cid], whys[cid] = model.predict_one(player, opponent, as_of)
                    for line in (0.5, 1.5, 2.5):
                        probs = {cid: d.prob_over(line) for cid, d in dists.items()}
                        if max(probs.values()) < 0.12 or min(probs.values()) > 0.97:
                            continue
                        rows.append(
                            {
                                "player": player,
                                "team": team,
                                "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
                                "kickoff": fx.kickoff_utc.isoformat(),
                                "market": market,
                                "line": line,
                                "probs": probs,
                                "whys": whys,
                            }
                        )
    return rows


def _preference(cid: str, row: dict) -> float:
    """How much this character wants this bet. Higher is keener.

    Boldness is deviation from the pack, NOT low probability. A character
    backing a 70% shot the others price at 55% is being bold; one backing a
    45% shot everybody agrees on is just accepting a longer price.
    """
    own = row["probs"][cid]
    others = [p for c, p in row["probs"].items() if c != cid]
    pack = sum(others) / len(others)
    edge = own - pack
    why = row["whys"][cid]

    if cid == "tayler":
        # Terror wants agreement and evidence, and dislikes standing out.
        return own - abs(edge) * 2.0 + min(why["effectiveMatches"], 40) / 200
    if cid == "alan":
        # Anger backs whatever it has most recently seen, hardest.
        return edge * 3.0 + why["ratePer90"] * 0.2
    if cid == "bdog":
        # Bravery goes where the pack is not, and tolerates thin evidence.
        return edge * 4.0 - min(why["effectiveMatches"], 40) / 400
    if cid == "valentina":
        # Violence reads the matchup above all else.
        return (why["opponentFactor"] - 1.0) * 4.0 + edge * 1.5
    # Lust chases the biggest raw numbers and the biggest names.
    return why["ratePer90"] * 1.5 + edge


def _equal_risk_slip(cid: str, candidates: list[dict], target=(0.10, 0.20)) -> list[dict]:
    """Five picks whose combined probability lands in a fixed band.

    Every character therefore risks the same and stands to win the same, so
    comparing them is finally apples to apples. Temperament shows in WHICH five
    get there, not in picking easier bets. See docs/15-next-phase.md.
    """
    ranked = sorted(candidates, key=lambda r: -_preference(cid, r))

    chosen: list[dict] = []
    seen: set[str] = set()
    combined = 1.0

    for row in ranked:
        if len(chosen) == PICKS_PER_CHARACTER:
            break
        if row["player"] in seen:
            continue
        p = row["probs"][cid]
        remaining = PICKS_PER_CHARACTER - len(chosen) - 1
        after = combined * p
        # Keep the slip reachable: with `remaining` legs still to add, the best
        # and worst it could still end up must straddle the target band.
        if after * (0.97**remaining) > target[1]:
            continue
        if after * (0.30**remaining) < target[0] and remaining > 0:
            continue
        chosen.append(row)
        seen.add(row["player"])
        combined = after

    if len(chosen) < PICKS_PER_CHARACTER:
        for row in ranked:
            if len(chosen) == PICKS_PER_CHARACTER:
                break
            if row["player"] in seen:
                continue
            chosen.append(row)
            seen.add(row["player"])
        combined = 1.0
        for row in chosen:
            combined *= row["probs"][cid]

    # Repair pass: swap the least-wanted leg for one that moves the slip toward
    # the band, keeping the character's preference order otherwise intact.
    for _ in range(60):
        if target[0] <= combined <= target[1]:
            break
        need_higher = combined < target[0]
        worst = min(range(len(chosen)), key=lambda i: _preference(cid, chosen[i]))
        current = chosen[worst]
        best_swap = None
        for row in ranked:
            if row["player"] in seen and row["player"] != current["player"]:
                continue
            candidate = combined / current["probs"][cid] * row["probs"][cid]
            if need_higher and candidate <= combined:
                continue
            if not need_higher and candidate >= combined:
                continue
            distance = min(abs(candidate - target[0]), abs(candidate - target[1]))
            if target[0] <= candidate <= target[1]:
                distance = -1.0
            if best_swap is None or distance < best_swap[0]:
                best_swap = (distance, row, candidate)
        if best_swap is None:
            break
        _, row, combined = best_swap
        seen.discard(current["player"])
        seen.add(row["player"])
        chosen[worst] = row

    return chosen


def _character_picks(cid, candidates) -> dict:
    c = characters.get(cid)
    chosen = _equal_risk_slip(cid, candidates)

    picks = []
    combined = 1.0
    for row in chosen:
        p = row["probs"][cid]
        why = row["whys"][cid]
        others = [q for k, q in row["probs"].items() if k != cid]
        pack = sum(others) / len(others)
        combined *= p
        picks.append(
            {
                "player": row["player"],
                "team": row["team"],
                "fixture": row["fixture"],
                "kickoff": row["kickoff"],
                "market": row["market"],
                "line": row["line"],
                "prob": round(p, 4),
                "packProb": round(pack, 4),
                "edge": round(p - pack, 4),
                "band": band(p),
                "outOf100": round(p * 100),
                "fair": round(1 / p, 2),
                "floor": round((1 / p) * (1 + EDGE_MARGIN), 2),
                "why": why,
                "thin": why["effectiveMatches"] < THIN_EVIDENCE,
            }
        )

    in_band = 0.10 <= combined <= 0.20
    return {
        "id": c.id,
        "name": c.name,
        "emotion": c.emotion,
        "tagline": c.tagline,
        "settings": pm.CHARACTER_SETTINGS[cid],
        "picks": picks,
        "combinedProb": round(combined, 4),
        "combinedFair": round(1 / combined, 1) if combined > 0 else None,
        "averageProb": round(sum(p["prob"] for p in picks) / len(picks), 3) if picks else 0,
        "averageEdge": round(sum(p["edge"] for p in picks) / len(picks), 4) if picks else 0,
        "inBand": in_band,
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
        flag = "" if block["inBand"] else "  [OUT OF BAND]"
        print(f"\n  {block['name']} ({block['emotion']}) — avg {block['averageProb']:.0%}, "
              f"combined {block['combinedFair']}/1, edge {block['averageEdge']:+.1%}{flag}")
        for p in block["picks"]:
            verb = "commits" if p["market"] == "committed" else "draws"
            print(f"    {p['player']:<22} {int(p['line']+0.5)}+ {verb:<7} "
                  f"{p['prob']:>5.0%} (pack {p['packProb']:>4.0%}) floor {p['floor']}")
