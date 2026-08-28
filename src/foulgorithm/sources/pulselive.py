"""Confirmed lineups, results and match events, from the Premier League's own API.

This is the source that finishes the lineup problem. It is unauthenticated,
free, and run by the league, and it carries the two things nothing else we hold
provides: the confirmed eleven roughly an hour before kickoff, and the result
minutes after full time.

Two operational notes:

  - It requires `Origin` and `Referer` headers pointing at premierleague.com.
    Without them the API refuses.
  - Fixture ids must be sent as integers. JSON parses them as floats, and
    "128923.0" returns a 400 that reads like a missing fixture rather than a
    formatting error.

⚠️ Terms. The Premier League's site terms restrict commercial use and bar
building a competing database from their content. Fine for a free, non-
commercial site publishing its own model output. Must be revisited before any
monetisation. See docs/13-legal-and-ethics.md.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from foulgorithm.sources.base import SourceError

BASE = "https://footballapi.pulselive.com/football"
HEADERS = {
    "User-Agent": "foulgorithm/0.1",
    "Origin": "https://www.premierleague.com",
    "Referer": "https://www.premierleague.com/",
}

# Competition 1 is the Premier League. Season ids change annually and are looked
# up rather than hard-coded, because hard-coding a season is what broke the 2025
# version every August.
COMPETITION = 1

# The league's API is not only the league's. It carries the FA Cup and the EFL
# Cup too, with the referee and the confirmed elevens attached, which is how the
# cup pages run without a second account to keep alive. Names on the right are
# OURS: Pulselive says "EFL Cup" and every slug, file and page here says
# "League Cup", so one spelling has to win and it is this one.
CUP_COMPETITIONS = {4: "FA Cup", 5: "League Cup"}

STATUS_COMPLETE = "C"
STATUS_UPCOMING = "U"
STATUS_LIVE = "L"


@dataclass(frozen=True)
class Lineup:
    fixture_id: int
    team_id: int
    formation: str | None
    starters: list[dict]
    substitutes: list[dict]


@dataclass(frozen=True)
class Fixture:
    id: int
    home: str
    away: str
    kickoff_utc: datetime
    status: str
    home_score: int | None
    away_score: int | None
    referee: str | None

    @property
    def complete(self) -> bool:
        return self.status == STATUS_COMPLETE


def forget() -> None:
    """Drop the cached fixture list, for a process that outlives its data.

    The lineup watcher runs for five and a half hours and exists to notice
    kickoff moves and referee appointments, so it must not be served a list it
    fetched at the start.
    """
    fixtures.cache_clear()
    current_season_id.cache_clear()


def _get(path: str) -> dict:
    request = urllib.request.Request(f"{BASE}/{path}", headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise SourceError(f"{path} returned HTTP {response.status}")
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{path} returned HTTP {exc.code}") from exc


@lru_cache(maxsize=1)
def current_season_id() -> int:
    """The newest Premier League season. Never hard-coded.

    Cached for the process. It was fetched once per call and a publish run asks
    a thousand times, which is a thousand identical round trips for a number
    that changes once a year.
    """
    data = _get(f"competitions/{COMPETITION}/compseasons?pageSize=5")
    seasons = data.get("content") or []
    if not seasons:
        raise SourceError("no Premier League seasons returned")
    return int(seasons[0]["id"])


@lru_cache(maxsize=4)
def fixtures(season_id: int | None = None, page_size: int = 100) -> list[Fixture]:
    """The season's fixture list.

    Cached for the process, which is the single biggest saving in a publish run.
    Profiling one showed 1,004 HTTP requests taking 89 of 232 seconds, almost
    all of them this list being fetched again inside a per-player loop, for data
    that does not change while the process is alive.

    Long-running jobs that must see kickoff changes call `forget()` first. The
    lineup watcher is the one that matters.
    """
    season = season_id or current_season_id()
    data = _get(f"fixtures?comps={COMPETITION}&compSeasons={season}&pageSize={page_size}&sort=asc")
    out = []
    for item in data.get("content") or []:
        teams = item.get("teams") or []
        if len(teams) != 2:
            continue
        officials = item.get("matchOfficials") or []
        referee = next(
            (
                (o.get("name") or {}).get("display")
                for o in officials
                if (o.get("role") or "").upper() == "MAIN"
            ),
            None,
        )
        out.append(
            Fixture(
                id=int(item["id"]),
                home=teams[0].get("team", {}).get("name", ""),
                away=teams[1].get("team", {}).get("name", ""),
                kickoff_utc=datetime.fromtimestamp(item["kickoff"]["millis"] / 1000, tz=UTC)
                if item.get("kickoff", {}).get("millis")
                else datetime.now(UTC),
                status=item.get("status", ""),
                home_score=teams[0].get("score"),
                away_score=teams[1].get("score"),
                referee=referee,
            )
        )
    return out


def cup_fixtures(competition: int, page_size: int = 100, pages: int = 3) -> list[dict]:
    """Raw cup fixtures, newest first.

    Sorted descending because the cups run for a season and we only ever want
    the near end of it: three pages of 100 covers a whole season's ties
    comfortably and never walks 2,700 rows of FA Cup history to find next
    week's fourth round.

    Returned raw rather than as `Fixture`, because a cup tie needs two fields
    the league's own list does not carry into that dataclass: the referee and
    the round.
    """
    out: list[dict] = []
    for page in range(pages):
        data = _get(f"fixtures?comps={competition}&pageSize={page_size}&sort=desc&page={page}")
        content = data.get("content") or []
        if not content:
            break
        out.extend(content)
    return out


def fixture_detail(fixture_id: int) -> dict:
    """Full detail: team lists, score, events, officials.

    `fixture_id` must be an int. Passing the float JSON gives you produces a 400
    that looks like a missing fixture.
    """
    return _get(f"fixtures/{int(fixture_id)}")


def lineups(fixture_id: int) -> list[Lineup]:
    """Confirmed elevens, empty until roughly an hour before kickoff."""
    detail = fixture_detail(fixture_id)
    out = []
    for team_list in detail.get("teamLists") or []:
        out.append(
            Lineup(
                fixture_id=int(fixture_id),
                team_id=int(team_list.get("teamId", 0)),
                formation=(team_list.get("formation") or {}).get("label")
                if isinstance(team_list.get("formation"), dict)
                else team_list.get("formation"),
                starters=[_person(p) for p in team_list.get("lineup") or []],
                substitutes=[_person(p) for p in team_list.get("substitutes") or []],
            )
        )
    return out


def _person(entry: dict) -> dict:
    name = entry.get("name") or {}
    return {
        "name": name.get("display") if isinstance(name, dict) else str(name),
        "position": entry.get("matchPosition"),
        "shirt": entry.get("matchShirtNumber"),
        "captain": bool(entry.get("captain")),
    }


def lineups_known_at(kickoff: datetime) -> datetime:
    """When a confirmed lineup becomes public.

    Roughly an hour before kickoff. Used as the `known_at` for anything derived
    from a lineup, so a prediction made two days earlier cannot claim to have
    seen it.
    """
    return kickoff - timedelta(hours=1)
