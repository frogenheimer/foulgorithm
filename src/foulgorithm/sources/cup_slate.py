"""The cup slate, from the Premier League's own API.

**The league's API is not only the league's.** It carries the FA Cup
(competition 4) and the EFL Cup (competition 5) as well, 2,730 and 1,676
fixtures deep, each with `matchOfficials` naming the referee and `teamLists`
carrying the confirmed elevens. It is free, unauthenticated, needs no key and
no card, and it is already this project's lineup source.

That last part is the reason it wins. API-Football could do this too, on paper,
but its free plan cannot see the current season at all (verified 26 August
2026, see docs/02) and its dedicated tiers want a card. Running the cups on a
source we already depend on means one account fewer to keep alive, and one
fewer thing that can quietly expire and take a page down.

**Most of a cup round is dropped, and that is the normal case.** An FA Cup
third round is 64 clubs and we hold match history for 44 of the 92 league
clubs. A tie involving anyone else is skipped without a word: a cup round
containing Salford is a cup round, not a bug. This is the one place in the
codebase where an unknown club is not an error, because here it genuinely is
not one.

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
from foulgorithm.sources import pulselive

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


def fetch(api=pulselive, now: datetime | None = None) -> list[dict]:
    """Upcoming ties from both cups, shaped for the publisher."""
    now = now or datetime.now(timezone.utc)

    ties: list[dict] = []
    for competition, name in sorted(api.CUP_COMPETITIONS.items()):
        for row in api.cup_fixtures(competition):
            tie = _shape(row, name, now)
            if tie is not None:
                ties.append(tie)

    ties.sort(key=lambda t: (t["kickoff_utc"], t["home_team_raw"]))
    return _assign_slugs(ties)


def _shape(row: dict, competition: str, now: datetime) -> dict | None:
    teams = row.get("teams") or []
    if len(teams) != 2:
        return None
    home = to_fixture_name((teams[0].get("team") or {}).get("name") or "")
    away = to_fixture_name((teams[1].get("team") or {}).get("name") or "")
    if not home or not away or not holds_data(home) or not holds_data(away):
        return None

    # A played tie is not upcoming however its clock reads. Checked before the
    # kickoff comparison, because a postponed-then-replayed fixture can carry a
    # future kickoff on a row that is already finished.
    if row.get("status") == pulselive.STATUS_COMPLETE:
        return None

    millis = (row.get("kickoff") or {}).get("millis")
    if millis is None:
        return None
    kickoff = datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)
    if kickoff <= now:
        return None

    referee = _referee(row)
    return {
        "home_team_raw": home,
        "away_team_raw": away,
        "kickoff_utc": kickoff,
        "known_at": now,
        # Normalised for the join, full spelling kept for the page. These were
        # one field and the join was silently finding nothing: football-data
        # writes "A Kitchen" and the league writes "Andrew Kitchen".
        "referee_raw": referees.normalise(referee),
        "referee_display": referees.display(referee),
        "competition": competition,
        # "2nd Round", from competitionPhase. The sibling `gameweek` field is
        # a number and renders as "2.0", which is not what a cup round is
        # called anywhere a reader would recognise.
        "round": _round(row),
        # int, never the float JSON gave us. Pulselive rejects "131355.0" with
        # a 400 that reads like a missing fixture. See sources/pulselive.
        "fixture_id": int(row["id"]),
        "kind": "full" if has_player_data(home) and has_player_data(away) else "total",
        "source": "pulselive",
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
    }


def _round(row: dict) -> str | None:
    """The round's name, as the competition calls it."""
    phase = (row.get("gameweek") or {}).get("competitionPhase") or {}
    return phase.get("label")


def _referee(row: dict) -> str | None:
    """The man in the middle, never one of his assistants."""
    for official in row.get("matchOfficials") or []:
        if official.get("role") == "MAIN":
            return (official.get("name") or {}).get("display")
    return None


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
