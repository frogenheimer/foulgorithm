"""Cup fixtures: hand-fed, predicted like any league game, recorded nowhere.

The fixture feeds know nothing but the Premier League, so a cup tie between
two of our twenty clubs cannot arrive on its own. It enters through
data/cup_fixtures.json by hand: home, away, kickoff_utc (with a timezone),
competition and, if known, the referee, all in the fixture spellings from
identity/teams.py.

Exhibition only, on purpose. The engine trains and predicts exactly as it
would for a league round, the payload lands at site/public/data/cup.json and
the fixture gets an archived page, but record=False keeps every ledger
untouched: no claims, no slates, no league scoring, no track-record noise
from games our results source will never grade. The contract (docs/38) is a
league of Premier League gameweeks, and a cup night is not quietly a fourth
bet in it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from foulgorithm.identity.teams import FIXTURE_TO_FPL
from foulgorithm.sources.base import SourceError

FIXTURES_FILE = Path("data/cup_fixtures.json")
OUTPUT = Path("site/public/data/cup.json")


def load_fixtures(path: Path = FIXTURES_FILE, now: datetime | None = None) -> list[dict]:
    """Upcoming hand-fed fixtures, shaped exactly like next_round.fetch rows."""
    now = now or datetime.now(timezone.utc)
    if not path.exists():
        return []

    out = []
    for row in json.loads(path.read_text()):
        for side in ("home", "away"):
            if row.get(side) not in FIXTURE_TO_FPL:
                raise SourceError(
                    f"unknown club {row.get(side)!r} in {path}. Cup fixtures use "
                    "the fixture spellings in identity/teams.py, "
                    "e.g. \"Nott'm Forest\", not \"Nottingham Forest\"."
                )
        kickoff = datetime.fromisoformat(str(row["kickoff_utc"]).replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            raise SourceError(
                f"kickoff for {row['home']} v {row['away']} must carry a timezone"
            )
        if kickoff <= now:
            continue
        out.append(
            {
                "home_team_raw": row["home"],
                "away_team_raw": row["away"],
                "kickoff_utc": kickoff,
                "known_at": now,
                "referee_raw": row.get("referee"),
                "odds_home": None,
                "odds_draw": None,
                "odds_away": None,
                "source": "hand-fed",
                "competition": row.get("competition", "Cup"),
            }
        )
    return out


def publish_cup(output: Path = OUTPUT) -> dict:
    """Predict the hand-fed slate. An empty slate still writes an honest file."""
    fixtures = load_fixtures()
    if not fixtures:
        payload = {
            "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "competition": "cup",
            "board": [],
            "expectedTotals": {},
            "fixtureSlips": {},
            "slates": {"byGame": {}},
            "picks": [],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, separators=(",", ":")))
        print("  no upcoming cup fixtures, wrote an empty slate")
        return payload

    from foulgorithm.publish import player_round

    return player_round.publish(
        output=output, fixtures_override=fixtures, record=False, competition="cup"
    )


if __name__ == "__main__":
    publish_cup()
