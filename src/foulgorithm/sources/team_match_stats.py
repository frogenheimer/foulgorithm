"""Around 180 team stats per match, every season back to 2006/07.

`stats/match/{id}` works on historical fixtures, not only current ones, and the
fixture list is available per season. That makes the league's own match data
reachable for twenty seasons at roughly 0.14 seconds a request.

**We hold about six team stats a match** from football-data.co.uk: fouls, cards,
shots, shots on target, corners, goals. This carries possession, touches by
third, duels, aerials, tackles, clearances, recoveries, where possession changed
hands, and `fk_foul_lost` / `fk_foul_won` / `attempted_tackle_foul` /
`fouled_final_third` throughout.

Roadmap item 9 proposes moving the opponent and referee factors onto live team
data. With this the opponent could be modelled on how a side actually plays
rather than on how many fouls it concedes.

One caution carried from `28-foul-data-sources.md`: this is the same provider as
the season totals, which read about 4.6% above the FBref archive on fouls. Mixing
either with the archive needs that term.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from foulgorithm.sources import pulselive

CACHE = Path("data/raw/pulselive/team_matches")

#: The league carries player fouls from 2006/07 and nothing before it. Team
#: stats follow the same boundary, so there is nothing to gain by going earlier.
FIRST_SEASON_END = 2007


def source_url(fixture_id: int) -> str:
    return f"{pulselive.BASE}/stats/match/{fixture_id}"


def shape(fixture_id: int, raw: dict) -> list[dict]:
    """One row per team, every stat a column.

    A team whose stat block is empty is dropped rather than written with zeros.
    Nothing recorded and a goalless defensive display are different facts, and a
    row of zeros would read as the second.
    """
    out = []
    for team_id, block in (raw.get("data") or {}).items():
        stats = block.get("M") or []
        if not stats:
            continue
        row = {"fixtureId": fixture_id, "teamId": str(team_id)}
        for stat in stats:
            name = stat.get("name")
            if name:
                row[name] = stat.get("value")
        out.append(row)
    return out


def fixtures_for(season_id: int) -> list[dict]:
    """Every fixture in one season, with ids and the two clubs."""
    payload = pulselive._get(
        f"fixtures?comps={pulselive.COMPETITION}&compSeasons={season_id}"
        f"&pageSize=500&sort=asc"
    )
    out = []
    for row in payload.get("content") or []:
        teams = [t.get("team", {}).get("name") for t in row.get("teams") or []]
        out.append(
            {
                "id": int(row["id"]),
                "home": teams[0] if teams else None,
                "away": teams[1] if len(teams) > 1 else None,
                "kickoff": (row.get("kickoff") or {}).get("label"),
            }
        )
    return out


def write_season(root: Path, label: str, season_id: int, rows: list[dict]) -> Path | None:
    """Write one season. An empty one is not written, for the usual reason."""
    if not rows:
        return None

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{label.replace('/', '-')}.json"
    path.write_text(
        json.dumps(
            {
                "season": label,
                "seasonId": season_id,
                "source": source_url(0).replace("/0", "/{fixture_id}"),
                "fetchedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "rows": len(rows),
                "teams": rows,
            },
            separators=(",", ":"),
        )
    )
    return path


def fetch_all(root: Path = CACHE) -> dict:
    """Every season from 2006/07, one file each. Skips what is already held."""
    from foulgorithm.sources.league_seasons import seasons

    root.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []

    for label, season_id in seasons():
        head = label.split("/")[0]
        if not head.isdigit() or int(head) + 1 < FIRST_SEASON_END:
            continue

        path = root / f"{label.replace('/', '-')}.json"
        if path.exists():
            skipped.append(label)
            continue

        rows: list[dict] = []
        missing = 0
        for fixture in fixtures_for(season_id):
            try:
                raw = pulselive._get(f"stats/match/{fixture['id']}")
            except Exception:  # noqa: BLE001 - counted, reported at the end
                missing += 1
                continue
            for row in shape(fixture["id"], raw):
                row["home"] = fixture["home"]
                row["away"] = fixture["away"]
                row["kickoff"] = fixture["kickoff"]
                rows.append(row)

        if write_season(root, label, season_id, rows):
            written.append((label, len(rows)))
            note = f", {missing} fixtures unavailable" if missing else ""
            print(f"  {label:<10}{len(rows):>5} team-matches{note}", flush=True)

    return {"written": written, "skipped": skipped}


def main() -> None:
    result = fetch_all()
    print()
    print(
        f"written {len(result['written'])} seasons, "
        f"skipped {len(result['skipped'])} already held"
    )


if __name__ == "__main__":
    main()
