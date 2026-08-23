"""Confirmed lineups for the upcoming round, keyed the way the rest of the code expects.

Wraps the Premier League API so callers get fixture-team names and plain player
names, rather than a third club spelling and a nested payload.

Confirmed lineups appear roughly an hour before kickoff. Before that this
returns nothing, and callers fall back to a predicted eleven. Those are
different products and are graded separately, per docs/07-backtesting.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from foulgorithm.identity.teams import from_pulselive
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
    # shape rather than inferred from position codes.
    lines: list[list[Spot]] = field(default_factory=list)
    bench: list[Spot] = field(default_factory=list)


def for_round(season_id: int | None = None, limit: int = 20) -> dict[str, ConfirmedLineup]:
    """Confirmed lineups keyed by "{team}|{fixture}".

    Only fixtures that are live or finished carry team lists, so an upcoming
    round returns an empty dict until an hour before its first kickoff.
    """
    out: dict[str, ConfirmedLineup] = {}
    fixtures = pulselive.fixtures(season_id)
    interesting = [f for f in fixtures if f.status in (pulselive.STATUS_LIVE, pulselive.STATUS_COMPLETE)]

    for fixture in interesting[-limit:]:
        try:
            home = from_pulselive(fixture.home)
            away = from_pulselive(fixture.away)
        except Exception:  # noqa: BLE001 - an unmapped club must not kill the round
            continue

        detail = pulselive.fixture_detail(fixture.id)
        team_ids = {}
        for entry in detail.get("teams") or []:
            team = entry.get("team") or {}
            if team.get("id") is not None:
                team_ids[int(team["id"])] = team.get("name")

        label = f"{home} v {away}"
        for team_list in detail.get("teamLists") or []:
            club = team_ids.get(int(team_list.get("teamId", -1)))
            if club is None:
                continue
            try:
                mapped = from_pulselive(club)
            except Exception:  # noqa: BLE001
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

            out[f"{mapped}|{label}"] = ConfirmedLineup(
                fixture=label,
                team=mapped,
                formation=formation,
                starters=[_name(p) for p in eleven],
                substitutes=[_name(p) for p in team_list.get("substitutes") or []],
                lines=lines,
                bench=[_spot(p) for p in team_list.get("substitutes") or []],
            )
    return out


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
