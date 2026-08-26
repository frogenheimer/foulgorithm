"""Every past meeting between two clubs, as a table of what happened.

Deliberately not `features/head_to_head`. That module computes a shrunk pairing
adjustment for the model, and it shrinks hard for good reason: across 9,120
matches and 428 pairings the split-half correlation is +0.138, a reliability of
about 0.24, so roughly three quarters of any observed pairing residual is noise.

Nothing here is shrunk, because nothing here is a prediction. It is a list of
meetings with the fouls each side committed, and every row names the division
it was played in so a second-tier meeting is not read as evidence about a
first-tier tie.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from foulgorithm.stats.team_record import DIVISION_NAMES


@dataclass(frozen=True)
class HeadToHead:
    home: str
    away: str
    meetings: int
    rows: list[dict] = field(default_factory=list)
    fouls: dict[str, float] = field(default_factory=dict)
    total_fouls: float | None = None


def build(home: str, away: str, matches: list[dict]) -> HeadToHead:
    """Meetings between the pair, newest first, in either direction."""
    pair = {home, away}
    met = [
        m for m in matches
        if {m["home_team_raw"], m["away_team_raw"]} == pair
    ]
    if not met:
        return HeadToHead(home=home, away=away, meetings=0)

    met.sort(key=lambda m: str(m.get("kickoff_utc") or ""), reverse=True)

    rows = [
        {
            "date": str(m.get("kickoff_utc") or "")[:10],
            "season": m.get("season"),
            "division": DIVISION_NAMES.get(m.get("division"), m.get("division")),
            "home": m["home_team_raw"],
            "away": m["away_team_raw"],
            "homeGoals": m.get("home_goals"),
            "awayGoals": m.get("away_goals"),
            "homeFouls": m["home_fouls"],
            "awayFouls": m["away_fouls"],
            "homeYellows": m.get("home_yellows"),
            "awayYellows": m.get("away_yellows"),
            "referee": m.get("referee_raw"),
        }
        for m in met
    ]

    def committed(club: str) -> float:
        values = [
            m["home_fouls"] if m["home_team_raw"] == club else m["away_fouls"]
            for m in met
        ]
        return round(sum(values) / len(values), 2)

    totals = [m["home_fouls"] + m["away_fouls"] for m in met]

    return HeadToHead(
        home=home,
        away=away,
        meetings=len(met),
        rows=rows,
        fouls={home: committed(home), away: committed(away)},
        total_fouls=round(sum(totals) / len(totals), 2),
    )
