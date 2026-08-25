"""The whole season as one list, with results where they exist.

The site showed one round. A reader arriving mid-season wants to move through
the campaign, see what has already happened, and check what a finished match
actually produced against what we said it would.

Results carry the three numbers this site is about: fouls committed, fouls won
and cards, per club. They come from the league's own match stats, which report
at team level, so this is what happened and not an estimate of it.

Stats are fetched once per completed fixture and cached in the published file,
because a finished match does not change.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("site/public/data/season.json")
CACHE = Path("data/state/match_stats.json")


def _referee(fixture_id: int, cache: dict) -> str | None:
    """The referee, which the fixtures LIST does not carry.

    Officials appear only on the per-fixture detail, so the list reports none
    for every match including ones already played. Fetched once per completed
    fixture and cached, because a finished match does not get a new referee.
    """
    key = f"ref:{fixture_id}"
    if key in cache:
        return cache[key]

    from foulgorithm.sources import pulselive

    try:
        detail = pulselive._get(f"fixtures/{fixture_id}")
    except Exception:
        return None

    name = next(
        (
            (o.get("name") or {}).get("display")
            for o in detail.get("matchOfficials") or []
            if (o.get("role") or "").upper() == "MAIN"
        ),
        None,
    )
    cache[key] = name
    return name


def _team_stats(fixture_id: int, cache: dict) -> dict | None:
    """Fouls, fouls won and cards per club. Cached: a finished match is finished."""
    key = str(fixture_id)
    if key in cache:
        return cache[key]

    from foulgorithm.sources import pulselive

    try:
        payload = pulselive._get(f"stats/match/{fixture_id}")
    except Exception:
        return None

    wanted = {"fk_foul_lost": "fouls", "fk_foul_won": "won", "total_yel_card": "cards"}
    out: dict[str, dict] = {}
    for team_id, block in (payload.get("data") or {}).items():
        stats = {}
        for metric in block.get("M") or []:
            if metric.get("name") in wanted:
                stats[wanted[metric["name"]]] = int(metric.get("value") or 0)
        if stats:
            out[str(team_id)] = stats

    if not out:
        return None
    cache[key] = out
    return out


def build() -> dict:
    from foulgorithm.identity.teams import from_pulselive
    from foulgorithm.sources import pulselive

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    raw = pulselive._get(
        f"fixtures?comps={pulselive.COMPETITION}"
        f"&compSeasons={pulselive.current_season_id()}&pageSize=400&sort=asc"
    )

    fixtures = []
    for item in raw.get("content") or []:
        teams = item.get("teams") or []
        if len(teams) != 2:
            continue
        gw = ((item.get("gameweek") or {}).get("gameweek")) or 0
        kickoff = (item.get("kickoff") or {}).get("millis")
        if not kickoff:
            continue

        try:
            home = from_pulselive(teams[0].get("team", {}).get("name", ""))
            away = from_pulselive(teams[1].get("team", {}).get("name", ""))
        except Exception:
            continue

        status = item.get("status", "")
        row = {
            "matchweek": int(gw),
            "home": home,
            "away": away,
            "kickoff": datetime.fromtimestamp(kickoff / 1000, tz=timezone.utc).isoformat(),
            "status": status,
            "referee": None,
        }

        if status == pulselive.STATUS_COMPLETE:
            row["referee"] = _referee(int(item["id"]), cache)
            row["score"] = [teams[0].get("score"), teams[1].get("score")]
            stats = _team_stats(int(item["id"]), cache)
            if stats:
                ids = [str(int(t.get("team", {}).get("id", -1))) for t in teams]
                row["result"] = {
                    side: stats.get(tid)
                    for side, tid in zip(("home", "away"), ids)
                    if stats.get(tid)
                }
        fixtures.append(row)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=2) + "\n")

    # Upcoming referees come from football-data, which publishes appointments
    # the league's fixture list does not carry.
    try:
        from foulgorithm.sources import football_data

        appointed = {
            (r["home_team_raw"], r["away_team_raw"]): r.get("referee_raw")
            for r in football_data.fetch_fixtures()
        }
        for row in fixtures:
            if not row["referee"]:
                row["referee"] = appointed.get((row["home"], row["away"]))
    except Exception:
        pass

    weeks = sorted({f["matchweek"] for f in fixtures if f["matchweek"]})
    played = [f for f in fixtures if f["status"] == pulselive.STATUS_COMPLETE]
    current = max((f["matchweek"] for f in played), default=weeks[0] if weeks else 1)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "matchweeks": weeks,
        "currentMatchweek": current,
        "fixtures": fixtures,
    }


def publish(output: Path = OUTPUT) -> dict:
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")))
    return payload


if __name__ == "__main__":
    r = publish()
    played = [f for f in r["fixtures"] if f.get("result")]
    print(f"{len(r['fixtures'])} fixtures across {len(r['matchweeks'])} matchweeks")
    print(f"current matchweek {r['currentMatchweek']}, {len(played)} with results\n")
    for f in played[:5]:
        h, a = f["result"].get("home", {}), f["result"].get("away", {})
        print(f"  MW{f['matchweek']} {f['home']} {f['score'][0]:.0f}-{f['score'][1]:.0f} {f['away']}"
              f"   fouls {h.get('fouls')}-{a.get('fouls')}  cards {h.get('cards')}-{a.get('cards')}")
