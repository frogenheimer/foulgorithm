"""Publish every character's view of the upcoming round.

All five see the same fixtures and the same history. Where they disagree is the
interesting part, so the export carries the spread per fixture as well as each
character's own numbers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from foulgorithm.characters import base as characters
from foulgorithm.markets import base as markets
from foulgorithm.models import character_models as cm
from foulgorithm.sources import football_data
from foulgorithm.store.matches import load_matches

OUTPUT = Path("site/public/data/characters.json")


def publish(output: Path = OUTPUT) -> dict:
    history = load_matches()
    fixtures = pd.DataFrame(football_data.fetch_fixtures())
    spec = markets.get("match_total_fouls")

    models = cm.build_all()
    per_character: dict[str, list] = {}
    for model in models:
        model.fit(history)
        per_character[model.character_id] = model.predict(fixtures)

    fixture_keys = [
        {
            "key": f"{row.home_team_raw}-{row.away_team_raw}",
            "home": row.home_team_raw,
            "away": row.away_team_raw,
            "kickoff": row.kickoff_utc.isoformat(),
            "referee": row.referee_raw,
        }
        for row in fixtures.itertuples()
    ]

    by_model = {m.character_id: m for m in models}

    # Every character gets an identity block; match-level predictions only
    # where a bespoke match model exists (the five). The challengers compete
    # through the player models, and their pages say who they are either way.
    character_blocks = []
    for c in characters.ALL:
        model = by_model.get(c.id)
        dists = per_character.get(c.id, [])
        character_blocks.append(
            {
                "id": c.id,
                "name": c.name,
                "emotion": c.emotion,
                "tagline": c.tagline,
                "philosophy": c.philosophy,
                "onLosing": c.on_losing,
                "weakness": c.weakness,
                "edge": c.edge,
                "generation": c.generation,
                "model": {
                    "id": model.id,
                    "version": model.version,
                    "config": {k: float(v) for k, v in model.config().items()},
                }
                if model
                else None,
                "fixtures": [
                    {
                        **fixture_keys[i],
                        "expectedFouls": round(d.mean(), 2),
                        "lines": [
                            {
                                "line": line,
                                "probOver": round(d.prob_over(line), 4),
                                "fairOddsOver": round(d.fair_odds_over(line), 2),
                            }
                            for line in spec.lines
                        ],
                        "pmf": [round(d.pmf(k), 5) for k in range(6, 45)],
                        "pmfFrom": 6,
                    }
                    for i, d in enumerate(dists)
                ],
            }
        )

    # Where the five disagree is the story, so compute it once here rather than
    # asking the site to work it out.
    disagreement = []
    for i, fx in enumerate(fixture_keys):
        means = {cid: dists[i].mean() for cid, dists in per_character.items() if len(dists) > i}
        values = np.array(list(means.values()))
        boldest = max(means, key=lambda k: abs(means[k] - values.mean()))
        disagreement.append(
            {
                **fx,
                "means": {k: round(v, 2) for k, v in means.items()},
                "consensus": round(float(values.mean()), 2),
                "spread": round(float(values.max() - values.min()), 2),
                "highest": max(means, key=means.get),
                "lowest": min(means, key=means.get),
                "boldest": boldest,
            }
        )

    payload = {
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "market": spec.key,
        "trainedOn": {
            "matches": len(history),
            "firstSeason": history["season"].min(),
            "lastSeason": history["season"].max(),
        },
        "characters": character_blocks,
        "disagreement": sorted(disagreement, key=lambda d: -d["spread"]),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    result = publish()
    print(f"Wrote {OUTPUT}\n")
    ids = [c["id"] for c in result["characters"]]
    header = f"{'fixture':<32}" + "".join(f"{i[:5]:>8}" for i in ids) + f"{'spread':>9}"
    print(header)
    print("-" * len(header))
    for d in result["disagreement"]:
        row = f"{d['home'] + ' v ' + d['away']:<32}"
        row += "".join(f"{d['means'][i]:>8.2f}" for i in ids)
        row += f"{d['spread']:>9.2f}"
        print(row)
    widest = result["disagreement"][0]
    print(
        f"\nWidest disagreement: {widest['home']} v {widest['away']}, "
        f"{widest['spread']} fouls between {widest['highest']} and {widest['lowest']}."
    )
