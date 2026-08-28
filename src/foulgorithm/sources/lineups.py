"""Confirmed lineups for the upcoming round, keyed the way the rest of the code expects.

Wraps the Premier League API so callers get fixture-team names and plain player
names, rather than a third club spelling and a nested payload.

Confirmed lineups appear roughly an hour before kickoff. Before that this
returns nothing, and callers fall back to a predicted eleven. Those are
different products and are graded separately, per docs/07-backtesting.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dataclasses import dataclass, field

from foulgorithm.identity.teams import from_pulselive, to_fixture_name
from foulgorithm.sources import pulselive


@dataclass(frozen=True)
class Spot:
    """One player in one slot of a formation."""

    name: str
    position: str         # G, D, M, F
    detail: str           # "Right Full Back", "Centre Defensive Midfielder"
    shirt: int | None
    captain: bool


@dataclass(frozen=True)
class ConfirmedLineup:
    fixture: str          # "Arsenal v Coventry", in fixture-source naming
    team: str             # fixture-source club name
    formation: str | None
    starters: list[str]
    substitutes: list[str]
    # The formation as LINES, goalkeeper first, each holding the players in it.
    # The league publishes this directly, so a pitch can be drawn from the real
    # shape rather than inferred from position codes. EMPTY when the source
    # published no formation, which happens: West Brom's League Cup sheet on
    # 26 Aug 2026 had eleven names and no shape.
    lines: list[list[Spot]] = field(default_factory=list)
    bench: list[Spot] = field(default_factory=list)
    # Every starter as a Spot, with or without a formation. `starters` is bare
    # names and `lines` is empty when no shape was published, so without this
    # a sheet with no formation loses each man's position entirely: five West
    # Brom players ended up in midfield and drew a back three behind a seven.
    spots: list[Spot] = field(default_factory=list)


def for_round(
    season_id: int | None = None, limit: int = 20, now: datetime | None = None
) -> dict[str, ConfirmedLineup]:
    """Confirmed lineups keyed by "{team}|{fixture}".

    Only fixtures that are live or finished carry team lists, so an upcoming
    round returns an empty dict until an hour before its first kickoff.
    """
    out: dict[str, ConfirmedLineup] = {}
    fixtures = pulselive.fixtures(season_id)
    # Upcoming fixtures DO carry team lists once the sheets are out: on 28
    # August 2026 Palace v City sat at status U with both elevens posted at
    # T-20 and this filter, which only read live or finished games, returned
    # nothing. Read any game kicking off in the next three hours as well; a
    # sheet not yet posted comes back as [null, null] and shapes to nothing.
    now = now or datetime.now(timezone.utc)
    interesting = [
        f
        for f in fixtures
        if f.status in (pulselive.STATUS_LIVE, pulselive.STATUS_COMPLETE)
        or (f.status == pulselive.STATUS_UPCOMING and now <= f.kickoff_utc <= now + timedelta(hours=3))
    ]

    interesting.sort(key=lambda f: f.kickoff_utc)
    for fixture in interesting[-limit:]:
        try:
            home = from_pulselive(fixture.home)
            away = from_pulselive(fixture.away)
        except Exception:  # noqa: BLE001 - an unmapped club must not kill the round
            continue

        label = f"{home} v {away}"
        out.update(shape_detail(pulselive.fixture_detail(fixture.id), label))
    return out


def shape_detail(detail: dict, label: str) -> dict[str, ConfirmedLineup]:
    """Pulselive's fixture detail to ConfirmedLineups, keyed "{team}|{fixture}".

    Shared by the league round and the cup watch. The league's API returns the
    same `teamLists` shape for a cup tie as for a league game, so there is one
    implementation of this and not two that drift.

    A club the maps do not know is SKIPPED rather than raised on. That is wrong
    for a league round, where all twenty resolve and a miss is a bug, and right
    for a cup, where half the draw is clubs we hold nothing for. The caller
    decides which situation it is in; this function refuses to guess and simply
    returns what it could name.
    """
    out: dict[str, ConfirmedLineup] = {}
    team_ids = {}
    for entry in detail.get("teams") or []:
        team = entry.get("team") or {}
        if team.get("id") is not None:
            team_ids[int(team["id"])] = team.get("name")

    for team_list in detail.get("teamLists") or []:
        # Before kickoff the source returns [null, null]: two placeholders
        # where the elevens will go, not an empty list. Calling .get() on
        # those is an AttributeError, and both watchers read this function.
        if not team_list:
            continue
        club = team_ids.get(int(team_list.get("teamId", -1)))
        if club is None:
            continue
        mapped = to_fixture_name(club)
        if mapped is None:
            continue
        raw_formation = team_list.get("formation")
        formation = raw_formation.get("label") if isinstance(raw_formation, dict) else raw_formation

        eleven = team_list.get("lineup") or []
        by_id = {int(p["id"]): p for p in eleven if p.get("id") is not None}

        # The league publishes the shape as lines of player ids, goalkeeper
        # first. Using it means a pitch is drawn from the real formation
        # rather than guessed from position codes, which cannot tell a back
        # three from a back four.
        lines: list[list[Spot]] = []
        if isinstance(raw_formation, dict):
            for row in raw_formation.get("players") or []:
                spots = [_spot(by_id[int(i)]) for i in row if int(i) in by_id]
                if spots:
                    lines.append(spots)
        if not lines and eleven:
            # No formation from the league (28 August 2026: Palace v City's
            # sheets arrived without one). An eleven with no lines was an
            # eleven with no pitch, because the publisher only draws a shape
            # from lines. Group by position instead, goalkeeper first; the
            # page already says "by position" when the formation is unknown.
            lines = _lines_by_position([_spot(p) for p in eleven])

        out[f"{mapped}|{label}"] = ConfirmedLineup(
            fixture=label,
            team=mapped,
            formation=formation,
            starters=[_name(p) for p in eleven],
            spots=[_spot(p) for p in eleven],
            substitutes=[_name(p) for p in team_list.get("substitutes") or []],
            lines=lines,
            bench=[_spot(p) for p in team_list.get("substitutes") or []],
        )
    return out


def _lines_by_position(spots: list[Spot]) -> list[list[Spot]]:
    """Lines inferred from position codes when the league gives no shape."""
    order = ("G", "D", "M", "F")
    grouped: dict[str, list[Spot]] = {code: [] for code in order}
    for spot in spots:
        code = (spot.position or "M")[:1].upper()
        grouped[code if code in grouped else "M"].append(spot)
    return [grouped[code] for code in order if grouped[code]]


def _spot(entry: dict) -> Spot:
    """One slot in a formation, with enough detail to place it left or right."""
    info = entry.get("info") or {}
    return Spot(
        name=_name(entry),
        position=str(entry.get("matchPosition") or info.get("position") or "?"),
        detail=str(info.get("positionInfo") or ""),
        shirt=entry.get("matchShirtNumber") or info.get("shirtNum"),
        captain=bool(entry.get("captain")),
    )


def _name(entry: dict) -> str:
    name = entry.get("name") or {}
    return name.get("display", "") if isinstance(name, dict) else str(name)
