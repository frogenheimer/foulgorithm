"""Per-fixture player statistics, including fouls, from API-Football.

**Why this source exists.** Our player-match history stops on 14 September 2025.
worldfootballR archived, and its data came from FBref, which now sits behind a
Cloudflare interactive challenge: even robots.txt is gated. Getting past that
means defeating a bot challenge rather than scraping politely, which is not
something to build. The league's own tables give season totals only, so a
player's fouls in one match are recoverable from them just as a difference
between two snapshots, and only going forward.

API-Football publishes fouls committed and fouls drawn per player per fixture
directly, which is the shape we actually need.

**Requires `API_FOOTBALL_KEY` in `.env`.** Without it every call raises rather
than returning empty, because a source that silently returns nothing looks
exactly like a quiet week.

Rate limits are real and low on the free plan, so `probe()` exists to answer
"what does this account actually give us" in a handful of requests rather than
discovering it halfway through a backfill.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from foulgorithm.sources.base import SourceError

BASE = "https://v3.football.api-sports.io"
PREMIER_LEAGUE = 39

#: Requests are metered, so anything fetched is kept.
CACHE = Path("data/raw/api_football")


def _key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY", "").strip()
    if not key:
        # Read .env directly rather than depending on a loader being called.
        env = Path(".env")
        if env.exists():
            # The LAST non-empty value wins. A .env that declares a name twice
            # is normal after a copy-paste from .env.example, and taking the
            # first match read the empty placeholder while a perfectly good key
            # sat twelve lines below it.
            for line in env.read_text().splitlines():
                if line.strip().startswith("API_FOOTBALL_KEY="):
                    value = line.split("=", 1)[1].strip().strip("\"'")
                    if value:
                        key = value
    if not key:
        raise SourceError(
            "API_FOOTBALL_KEY is empty. Paste the key from your API-Football "
            "dashboard into .env; it is never read from anywhere else."
        )
    return key


def _get(path: str, params: dict | None = None) -> dict:
    query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    url = f"{BASE}/{path}" + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url, headers={"x-apisports-key": _key(), "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise SourceError(f"{path} returned HTTP {response.status}")
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{path} returned HTTP {exc.code}") from exc

    # The API answers 200 with an errors object rather than an error status,
    # so a plan or quota problem arrives looking like success.
    errors = payload.get("errors")
    if errors:
        raise SourceError(f"{path}: {errors}")
    return payload


@dataclass(frozen=True)
class Coverage:
    """What this account can actually see."""

    plan_ok: bool
    seasons: list[int]
    fixtures_in_season: int
    has_player_fouls: bool
    requests_used: int | None
    requests_limit: int | None
    note: str


def probe(season: int = 2025) -> Coverage:
    """Answer, in four requests, whether this account can fill the gap.

    Three things decide it: does the key work, does the season have fixtures,
    and do per-fixture player statistics carry fouls. Anything else is detail.
    """
    status = _get("status")
    response = status.get("response") or {}
    requests = (response.get("requests") or {})

    seasons = _get("leagues/seasons").get("response") or []

    fixtures = _get("fixtures", {"league": PREMIER_LEAGUE, "season": season})
    rows = fixtures.get("response") or []

    has_fouls = False
    note = "no finished fixture found to sample"
    if rows:
        finished = [
            f for f in rows if (f.get("fixture", {}).get("status", {}).get("short")) == "FT"
        ]
        sample = (finished or rows)[0]
        detail = _get("fixtures/players", {"fixture": sample["fixture"]["id"]})
        for side in detail.get("response") or []:
            for player in side.get("players") or []:
                for block in player.get("statistics") or []:
                    fouls = block.get("fouls") or {}
                    if fouls.get("committed") is not None or fouls.get("drawn") is not None:
                        has_fouls = True
        note = (
            f"sampled fixture {sample['fixture']['id']}, "
            f"{'fouls present' if has_fouls else 'NO fouls in player statistics'}"
        )

    return Coverage(
        plan_ok=True,
        seasons=[int(s) for s in seasons if str(s).isdigit()],
        fixtures_in_season=len(rows),
        has_player_fouls=has_fouls,
        requests_used=requests.get("current"),
        requests_limit=requests.get("limit_day"),
        note=note,
    )


def player_fouls(fixture_id: int) -> list[dict]:
    """Fouls committed and drawn for every player in one fixture.

    Returns rows shaped like the player-match store, so a backfill is a matter
    of concatenating these rather than reshaping them later.
    """
    payload = _get("fixtures/players", {"fixture": fixture_id})
    out = []
    for side in payload.get("response") or []:
        team = (side.get("team") or {}).get("name")
        for player in side.get("players") or []:
            name = (player.get("player") or {}).get("name")
            for block in player.get("statistics") or []:
                fouls = block.get("fouls") or {}
                games = block.get("games") or {}
                out.append(
                    {
                        "player": name,
                        "team": team,
                        "minutes": games.get("minutes") or 0,
                        "position": games.get("position"),
                        "fouls_committed": fouls.get("committed"),
                        "fouls_drawn": fouls.get("drawn"),
                        "yellows": (block.get("cards") or {}).get("yellow"),
                        "reds": (block.get("cards") or {}).get("red"),
                        "source": "api-football",
                    }
                )
    return out


def main() -> None:
    """`make api-football-probe`. Says what the account gives us, and no more."""
    try:
        coverage = probe()
    except SourceError as exc:
        print(f"not usable yet: {exc}")
        return

    print(f"key works            yes")
    print(f"seasons visible      {len(coverage.seasons)}")
    print(f"2025 fixtures        {coverage.fixtures_in_season}")
    print(f"player fouls         {'YES' if coverage.has_player_fouls else 'NO'}")
    print(f"requests today       {coverage.requests_used} of {coverage.requests_limit}")
    print()
    print(coverage.note)
    if coverage.has_player_fouls:
        need = coverage.fixtures_in_season
        limit = coverage.requests_limit or 100
        print()
        print(
            f"A full season backfill costs about {need} requests. "
            f"At {limit} a day that is {max(1, -(-need // limit))} day(s)."
        )


if __name__ == "__main__":
    main()
