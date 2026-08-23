"""Current Premier League squads, from the official Fantasy Premier League API.

Why this source. Our foul history ends September 2025, so deriving squads from
it names players who have since transferred and misses every summer signing. A
prediction about a player who is not in the squad is wrong, not weak.

FPL is unauthenticated, free, updates constantly and is run by the league
itself. It carries no foul data, which does not matter: we need it for WHO IS
IN THE SQUAD, and the foul rates come from history.

It also carries availability, which is a genuine bonus. `status` and
`chance_of_playing_next_round` tell us who is injured or suspended, so an
unavailable player can be dropped before he ever reaches a prediction.
"""

from __future__ import annotations

import json
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from foulgorithm.sources.base import SourceError, utcnow

BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES = "https://fantasy.premierleague.com/api/fixtures/"
CACHE = Path("data/raw/fpl")
# Squads change slowly; a short cache keeps development offline without going stale.
CACHE_TTL = timedelta(hours=6)

POSITIONS = {1: "GK", 2: "DF", 3: "MF", 4: "FW"}

# FPL status codes. Anything not "a" means the player is doubtful or unavailable,
# and "u" specifically means he has left: the news field on those reads "Has
# joined X permanently" or "on loan". Worth separating, because a sold player and
# an injured one are different facts. An injured centre back is still in the
# squad and belongs in a squad table; a sold one belongs only in the history the
# models train on.
AVAILABLE = "a"
DEPARTED = "u"


@dataclass(frozen=True)
class SquadPlayer:
    name: str
    web_name: str
    team: str
    position: str
    available: bool
    chance: int | None
    news: str
    minutes: int
    starts: int
    status: str = AVAILABLE

    @property
    def departed(self) -> bool:
        """Left the club. Not selectable anywhere, still valid training data."""
        return self.status == DEPARTED

    @property
    def key(self) -> str:
        return normalise(self.name)


def normalise(name: str) -> str:
    """Strip accents, punctuation and case so two spellings can be compared.

    Used only to GENERATE a match. It never confirms one on its own, per
    docs/decisions/ADR-007-identity-halts-pipeline.md.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum() or c == " ").strip()


def _fetch(url: str, cache_name: str) -> dict:
    cache = CACHE / cache_name
    if cache.exists() and utcnow() - _mtime(cache) < CACHE_TTL:
        return json.loads(cache.read_text())

    request = urllib.request.Request(url, headers={"User-Agent": "foulgorithm/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise SourceError(f"{url} returned HTTP {response.status}")
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        raise SourceError(f"{url} returned HTTP {exc.code}") from exc

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload))
    return payload


def _mtime(path: Path):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def current_squads() -> dict[str, list[SquadPlayer]]:
    """Every club's current squad, keyed by the FPL club name."""
    data = _fetch(BOOTSTRAP, "bootstrap.json")
    teams = {t["id"]: t["name"] for t in data.get("teams", [])}
    if len(teams) != 20:
        raise SourceError(f"expected 20 clubs from FPL, got {len(teams)}")

    squads: dict[str, list[SquadPlayer]] = {name: [] for name in teams.values()}
    for element in data.get("elements", []):
        team = teams.get(element["team"])
        if team is None:
            continue
        full = f"{element['first_name']} {element['second_name']}".strip()
        squads[team].append(
            SquadPlayer(
                name=full,
                web_name=element.get("web_name", full),
                team=team,
                position=POSITIONS.get(element.get("element_type"), "?"),
                status=(element.get("status") or AVAILABLE),
                available=element.get("status") == AVAILABLE,
                chance=element.get("chance_of_playing_next_round"),
                news=(element.get("news") or "").strip(),
                minutes=int(element.get("minutes") or 0),
                starts=int(element.get("starts") or 0),
            )
        )
    return squads


def at_the_club(players: list[SquadPlayer]) -> list[SquadPlayer]:
    """Everyone still at the club, injured and suspended included."""
    return [p for p in players if not p.departed]


def likely_eleven(players: list[SquadPlayer], size: int = 14) -> list[SquadPlayer]:
    """Best available guess at who features, before confirmed lineups exist.

    Ranked on this season's starts then minutes, with anyone flagged unavailable
    removed. Crude while the season is days old, and it improves every week as
    real minutes accumulate. Clearly a PREDICTION, and the site must say so.
    """
    fit = [p for p in players if p.available and (p.chance is None or p.chance >= 75)]
    fit.sort(key=lambda p: (-p.starts, -p.minutes))
    return fit[:size]
