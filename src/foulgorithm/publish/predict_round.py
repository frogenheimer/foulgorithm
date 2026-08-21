"""Predict the next round of fixtures and write them for the site.

The champion model, fitted on everything knowable now, applied to the upcoming
round. Output is a full distribution per fixture, so every line is priced from
one fit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from foulgorithm.features import match_features as mf
from foulgorithm.markets import base as markets
from foulgorithm.models.match_models import TeamRatesReferee
from foulgorithm.sources import football_data
from foulgorithm.store.matches import load_matches

CHAMPION = TeamRatesReferee
OUTPUT = Path("site/public/data/round.json")

# Below this many time-decayed matches, a rate is mostly the league prior and
# the site should say so rather than present it as a read on the team.
THIN_EVIDENCE = 10.0


def predict_round(output: Path = OUTPUT) -> dict:
    history = load_matches()
    fixtures = pd.DataFrame(football_data.fetch_fixtures())
    spec = markets.get("match_total_fouls")

    model = CHAMPION()
    model.fit(history)
    distributions = model.predict(fixtures)

    predictions = []
    for (_, row), dist in zip(fixtures.iterrows(), distributions, strict=True):
        # Confidence is judged on EFFECTIVE sample size, not on whether a name
        # appears in the data at all. Coventry played in this league until 2001,
        # so a membership test would call them known while time decay has quite
        # correctly discounted that history to almost nothing.
        ctx = mf.build_context(
            history,
            row.home_team_raw,
            row.away_team_raw,
            row.referee_raw,
            row.kickoff_utc,
            half_life_days=model.half_life_days,
        )
        thin = []
        if ctx.home_matches < THIN_EVIDENCE:
            thin.append(f"{row.home_team_raw} ({ctx.home_matches:.1f} effective matches)")
        if ctx.away_matches < THIN_EVIDENCE:
            thin.append(f"{row.away_team_raw} ({ctx.away_matches:.1f} effective matches)")
        if row.referee_raw and ctx.referee_matches < THIN_EVIDENCE:
            thin.append(f"{row.referee_raw}, referee ({ctx.referee_matches:.1f} effective)")

        predictions.append(
            {
                "kickoff": row.kickoff_utc.isoformat(),
                "home": row.home_team_raw,
                "away": row.away_team_raw,
                "referee": row.referee_raw,
                "expectedFouls": round(dist.mean(), 2),
                "lines": [
                    {
                        "line": line,
                        "probOver": round(dist.prob_over(line), 4),
                        "fairOddsOver": round(dist.fair_odds_over(line), 2),
                        "fairOddsUnder": round(1 / (1 - dist.prob_over(line)), 2),
                    }
                    for line in spec.lines
                ],
                "pmf": [round(dist.pmf(k), 5) for k in range(6, 45)],
                "pmfFrom": 6,
                "thinEvidence": thin,
                "effectiveMatches": {
                    "home": round(ctx.home_matches, 1),
                    "away": round(ctx.away_matches, 1),
                    "referee": round(ctx.referee_matches, 1),
                },
            }
        )

    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model": {
            "id": model.id,
            "version": model.version,
            "config": {k: float(v) for k, v in model.config().items()},
        },
        "market": spec.key,
        "trainedOn": {
            "matches": len(history),
            "firstSeason": history["season"].min(),
            "lastSeason": history["season"].max(),
        },
        "fixtures": predictions,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    result = predict_round()
    print(f"Model: {result['model']['id']} {result['model']['version']}")
    print(f"Trained on {result['trainedOn']['matches']} matches\n")
    header = f"{'fixture':<34}{'referee':<14}{'xFouls':>8}{'o22.5':>8}{'fair':>7}"
    print(header)
    print("-" * len(header))
    for f in result["fixtures"]:
        line = next(x for x in f["lines"] if x["line"] == 22.5)
        fixture = f"{f['home']} v {f['away']}"
        flag = " *" if f["thinEvidence"] else ""
        print(
            f"{fixture:<34}{(f['referee'] or '-'):<14}{f['expectedFouls']:>8.2f}"
            f"{line['probOver']:>8.1%}{line['fairOddsOver']:>7.2f}{flag}"
        )
    flagged = [f for f in result["fixtures"] if f["thinEvidence"]]
    if flagged:
        print("\n* leaning on the league prior, thin evidence for:")
        for f in flagged:
            print(f"    {f['home']} v {f['away']}: {', '.join(f['thinEvidence'])}")
