"""The cup slate, pulled from API-Football rather than hand-fed.

`data/cup_fixtures.json` required somebody to notice a tie and type it in. The
draw is public, API-Football already carries both domestic cups, and the ids
were already in this package, so the slate builds itself now.

**Most of a cup round is dropped, and that is the normal case.** An FA Cup
third round is 64 clubs and we hold match history for 44 of them. A tie
involving anyone else is skipped without a word: a cup round containing Salford
is a cup round, not a bug. This is the one place in the codebase where an
unknown club is not an error, because here it genuinely is not one.

Two things every tie carries out of here.

**A slug that cannot collide.** The old '-cup' suffix put both cups on one
page, so Arsenal v Chelsea in the FA Cup and the same pairing in the League Cup
were the same URL. The competition is in the slug now, and a repeat meeting in
the same cup (a replay, or the second leg of a semi) takes a numbered suffix in
kickoff order.

**A `kind`, which decides what may be published about it.** `full` means both
clubs are Premier League and the player model can run. `total` means at least
one is a Championship club, where no player-level foul data exists at any
price, so the tie gets a match total and its raw record and no player pick. See
identity.teams.has_player_data, which is what enforces it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from foulgorithm.identity import referees
from foulgorithm.identity.teams import has_player_data, holds_data, to_fixture_name
from foulgorithm.sources import api_football

#: Slug fragment per competition. Written down rather than derived from the
#: name, so a rename upstream cannot silently move every page's URL.
COMPETITION_SLUGS = {"FA Cup": "fa-cup", "League Cup": "league-cup"}


def slug(home: str, away: str, competition: str, repeat: int = 1) -> str:
    """The tie's page slug. Never equal to the league fixture's, ever.

    `repeat` numbers a second meeting of the same pairing in the same cup, in
    kickoff order. The first keeps the bare slug so an existing link to a
    single-legged tie does not move when a replay is added.
    """
    label = re.sub(r"[^a-z0-9]+", "-", f"{home} v {away}".lower()).strip("-")
    suffix = COMPETITION_SLUGS.get(competition)
    if suffix is None:
        raise ValueError(f"no slug fragment for competition {competition!r}")
    return f"{label}-{suffix}" + (f"-{repeat}" if repeat > 1 else "")


def _season_for(kickoff: datetime) -> int:
    return kickoff.year if kickoff.month >= 7 else kickoff.year - 1


def fetch(api=api_football, now: datetime | None = None, season: int | None = None) -> list[dict]:
    """Upcoming ties from both cups, shaped for the publisher.

    One request per cup. That matters: the free plan meters 100 requests a day
    and the lineup watch spends most of them.
    """
    now = now or datetime.now(timezone.utc)
    season = season if season is not None else _season_for(now)

    ties: list[dict] = []
    for league_id, competition in sorted(api.CUP_LEAGUES.items()):
        rows = api._get("fixtures", {"league": league_id, "season": season}).get("response") or []
        for row in rows:
            tie = _shape(row, competition, now)
            if tie is not None:
                ties.append(tie)

    ties.sort(key=lambda t: (t["kickoff_utc"], t["home_team_raw"]))
    return _assign_slugs(ties)


def _shape(row: dict, competition: str, now: datetime) -> dict | None:
    teams = row.get("teams") or {}
    home = to_fixture_name((teams.get("home") or {}).get("name") or "")
    away = to_fixture_name((teams.get("away") or {}).get("name") or "")
    if not home or not away or not holds_data(home) or not holds_data(away):
        return None

    fixture = row.get("fixture") or {}
    raw_kickoff = fixture.get("date")
    if not raw_kickoff:
        return None
    kickoff = datetime.fromisoformat(str(raw_kickoff).replace("Z", "+00:00"))
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    if kickoff <= now:
        return None

    referee = fixture.get("referee")
    return {
        "home_team_raw": home,
        "away_team_raw": away,
        "kickoff_utc": kickoff,
        "known_at": now,
        # Normalised for the join, full spelling kept for the page. These were
        # one field and the join was silently finding nothing.
        "referee_raw": referees.normalise(referee),
        "referee_display": referees.display(referee),
        "competition": competition,
        "round": (row.get("league") or {}).get("round"),
        "fixture_id": fixture.get("id"),
        "kind": "full" if has_player_data(home) and has_player_data(away) else "total",
        "source": "api-football",
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
    }


def _assign_slugs(ties: list[dict]) -> list[dict]:
    """Number repeat meetings of a pairing within one cup, in kickoff order."""
    seen: dict[tuple[str, str, str], int] = {}
    for tie in ties:
        key = (tie["home_team_raw"], tie["away_team_raw"], tie["competition"])
        seen[key] = seen.get(key, 0) + 1
        tie["slug"] = slug(
            tie["home_team_raw"], tie["away_team_raw"], tie["competition"], repeat=seen[key]
        )
    return ties
