"""Where each player was last actually seen playing.

The league's confirmed team sheets say what a player's role WAS that day
("Right Full Back", "Centre Defensive Midfielder"); FPL's squad codes only
say which bucket he scores fantasy points in. The predicted pitch needs the
former: FPL codes wing-backs and pushed-up full-backs as defenders, and a
back seven drawn from those codes is a shape no team has ever played. This
store keeps the last seen role per player, updated every time confirmed
lineups arrive, so each predicted pitch is a little less wrong than the
last. Names are matched with accents folded, because the league writes
Magalhães and the squad feed writes Magalhaes.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

STATE = Path("data/state/positions_seen.json")


def norm(name: str | None) -> str:
    folded = unicodedata.normalize("NFKD", name or "")
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(folded.lower().split())


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def remember(lineups: dict, path: Path = STATE) -> None:
    """Record each starter's role from confirmed team sheets. Latest wins."""
    if not lineups:
        return
    held = _read(path)
    seen_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    changed = False
    for lineup in lineups.values():
        for line in getattr(lineup, "lines", []) or []:
            for spot in line:
                detail = getattr(spot, "detail", "") or ""
                name = getattr(spot, "name", "") or ""
                if not detail or not name:
                    continue
                held[norm(name)] = {"name": name, "detail": detail, "seenAt": seen_at}
                changed = True
    if not changed:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=1, sort_keys=True) + "\n")


def load(path: Path = STATE) -> dict[str, str]:
    """Normalised player name -> last seen role detail."""
    return {
        key: row.get("detail", "")
        for key, row in _read(path).items()
        if isinstance(row, dict)
    }


def role_for(roles: dict[str, str], name: str | None) -> str:
    return roles.get(norm(name), "")
