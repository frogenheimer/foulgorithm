"""The league table, and every club's discipline record behind it.

A table is the natural way into a season, and this one carries the columns this
site is actually about alongside the ones everyone expects. Points and goals
place a club; fouls, fouls won and cards are what we model.

Player rows come from the same history the models train on, restricted to the
club's CURRENT squad. Listing whoever appeared in the window puts players who
left a year ago in a table about this season, which is a mistake already made
once on the stats sheet.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUTPUT = Path("site/public/data/teams.json")

# Real playing time, not appearances. Three outings of nine minutes is a third
# of a match, and a per-90 rate off that is noise wearing a number.
MIN_NINETIES = 3.0


def _division() -> set[str]:
    """Every club in the league this season, from the fixture list."""
    from foulgorithm.identity.teams import from_pulselive
    from foulgorithm.sources import pulselive

    try:
        clubs = set()
        for f in pulselive.fixtures():
            for raw in (f.home, f.away):
                clubs.add(from_pulselive(raw))
        return clubs
    except Exception:
        return set()


def _current_season() -> pd.DataFrame:
    """Completed matches this season, in football-data's column shape.

    Scores come from the league. Fouls and cards do not: those are per-fixture
    stat calls and the table does not need them, since the rates alongside it
    come from the longer window.
    """
    from foulgorithm.identity.teams import from_pulselive
    from foulgorithm.sources import pulselive

    try:
        raw = pulselive._get(
            f"fixtures?comps={pulselive.COMPETITION}"
            f"&compSeasons={pulselive.current_season_id()}&pageSize=400&sort=asc"
        )
    except Exception:
        return pd.DataFrame()

    rows = []
    for item in raw.get("content") or []:
        if item.get("status") != pulselive.STATUS_COMPLETE:
            continue
        teams = item.get("teams") or []
        if len(teams) != 2:
            continue
        try:
            home = from_pulselive(teams[0].get("team", {}).get("name", ""))
            away = from_pulselive(teams[1].get("team", {}).get("name", ""))
        except Exception:
            continue
        rows.append(
            {
                "home_team_raw": home,
                "away_team_raw": away,
                "home_goals": teams[0].get("score"),
                "away_goals": teams[1].get("score"),
            }
        )
    return pd.DataFrame(rows)


def _table(matches: pd.DataFrame) -> list[dict]:
    """Points, goals and discipline per club, from completed matches."""
    rows: dict[str, dict] = {}

    def blank(club: str) -> dict:
        return {
            "team": club, "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "goalsFor": 0, "goalsAgainst": 0, "points": 0,
            "fouls": [], "foulsWon": [], "cards": [],
        }

    for m in matches.itertuples():
        if pd.isna(getattr(m, "home_goals", None)) or pd.isna(getattr(m, "away_goals", None)):
            continue
        h, a = m.home_team_raw, m.away_team_raw
        for club in (h, a):
            rows.setdefault(club, blank(club))

        hg, ag = int(m.home_goals), int(m.away_goals)
        rows[h]["played"] += 1
        rows[a]["played"] += 1
        rows[h]["goalsFor"] += hg
        rows[h]["goalsAgainst"] += ag
        rows[a]["goalsFor"] += ag
        rows[a]["goalsAgainst"] += hg

        if hg > ag:
            rows[h]["won"] += 1; rows[a]["lost"] += 1; rows[h]["points"] += 3
        elif ag > hg:
            rows[a]["won"] += 1; rows[h]["lost"] += 1; rows[a]["points"] += 3
        else:
            rows[h]["drawn"] += 1; rows[a]["drawn"] += 1
            rows[h]["points"] += 1; rows[a]["points"] += 1

        for club, own, other in ((h, "home", "away"), (a, "away", "home")):
            for key, field in (("fouls", "fouls"), ("cards", "yellows")):
                mine = getattr(m, f"{own}_{field}", None)
                if mine is not None and not pd.isna(mine):
                    rows[club][key].append(float(mine))
            theirs = getattr(m, f"{other}_fouls", None)
            if theirs is not None and not pd.isna(theirs):
                rows[club]["foulsWon"].append(float(theirs))

    out = []
    for club, r in rows.items():
        out.append(
            {
                **{k: v for k, v in r.items() if k not in ("fouls", "foulsWon", "cards")},
                "goalDifference": r["goalsFor"] - r["goalsAgainst"],
                "foulsPerMatch": round(statistics.fmean(r["fouls"]), 2) if r["fouls"] else None,
                "foulsWonPerMatch": round(statistics.fmean(r["foulsWon"]), 2) if r["foulsWon"] else None,
                "cardsPerMatch": round(statistics.fmean(r["cards"]), 2) if r["cards"] else None,
            }
        )
    return sorted(out, key=lambda r: (-r["points"], -r["goalDifference"], -r["goalsFor"]))


def _players(history: pd.DataFrame, club: str, squad: set[str] | None) -> list[dict]:
    """Everyone in the club's current squad, with what they actually do."""
    rows = history[history["team"] == club]
    if squad is not None:
        rows = rows[rows["player"].isin(squad)]
    if rows.empty:
        return []

    g = rows.groupby("player")
    nineties = g["minutes"].sum() / 90.0
    stats = pd.DataFrame(
        {
            "matches": g.size(),
            "minutes": g["minutes"].sum(),
            "nineties": nineties,
            "fouls": g["fouls_committed"].sum(),
            "won": g["fouls_drawn"].sum(),
            "cards": g["yellows"].sum(),
            "tackles": g["tackles_won"].sum(),
            "position": g["position"].last(),
        }
    )
    stats = stats[stats["nineties"] >= MIN_NINETIES]
    if stats.empty:
        return []

    out = []
    for player, r in stats.sort_values("fouls", ascending=False).iterrows():
        n = float(r["nineties"])
        out.append(
            {
                "player": player,
                "position": str(r["position"] or "").split(",")[0].strip(),
                "matches": int(r["matches"]),
                "minutes": int(r["minutes"]),
                "foulsPer90": round(float(r["fouls"]) / n, 2),
                "wonPer90": round(float(r["won"]) / n, 2),
                "tacklesPer90": round(float(r["tackles"]) / n, 2),
                "cards": int(r["cards"]),
            }
        )
    return out


def build(seasons: int = 2) -> dict:
    from foulgorithm.identity.teams import history_name
    from foulgorithm.publish.site_export import season_labels
    from foulgorithm.sources import football_data
    from foulgorithm.store.players import load_player_matches

    labels = season_labels()[-seasons:]
    frames = []
    for label in labels:
        try:
            frames.append(pd.DataFrame(football_data.parse(football_data.fetch(label))))
        except Exception:
            continue
    matches = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # The current season's results come from the league's own feed.
    # football-data does not publish a season's file until it is well under way,
    # and falling back to the previous season silently produced a table showing
    # 38 played in the first week of a campaign.
    current_matches, table_season = _current_season(), labels[-1]
    if current_matches.empty:
        current_matches, table_season = matches, f"{labels[0]} to {labels[-1]}"

    history = load_player_matches()
    cutoff = history["kickoff_utc"].max() - pd.Timedelta(days=400 * seasons)
    history = history[history["kickoff_utc"] >= cutoff]

    # Current squads, so a player who left last summer is not in a table about
    # this season. Same rule as the stats sheet.
    squads: dict[str, set[str]] = {}
    try:
        from foulgorithm.identity import players as identity
        from foulgorithm.identity.teams import to_fpl
        from foulgorithm.sources import fpl

        live = fpl.current_squads()
        everyone = [p for club in live.values() for p in club]
        resolution = identity.resolve(everyone, history["player"].unique())
        by_fpl = {
            club: {resolution.matched[p.name] for p in members if p.name in resolution.matched}
            for club, members in live.items()
        }
    except Exception:
        by_fpl, to_fpl = {}, None

    # Two different windows, on purpose. A league table means THIS season, however
    # few matches have been played. Foul rates want more than a week of evidence,
    # so they come from the longer window and the page labels both.
    current = _table(current_matches)
    rates = {r["team"]: r for r in _table(matches)}

    # Every club in the division, not only those who have played. In the first
    # week of a season a table built from completed matches alone shows twelve
    # teams, which reads as a bug because it is one.
    # This season's twenty, from the live fixture list. Taking them from the rate
    # window instead pulled in last season's relegated clubs and produced a
    # twenty-three team division.
    division = _division() or set(rates)
    current = [r for r in current if r["team"] in division]
    played = {r["team"] for r in current}
    for club in division:
        if club not in played:
            current.append(
                {
                    "team": club, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                    "goalsFor": 0, "goalsAgainst": 0, "goalDifference": 0, "points": 0,
                }
            )
    current.sort(key=lambda r: (-r["points"], -r["goalDifference"], -r["goalsFor"], r["team"]))

    table = []
    for row in current:
        long_run = rates.get(row["team"], {})
        table.append(
            {
                **{k: v for k, v in row.items() if not k.endswith("PerMatch")},
                "foulsPerMatch": long_run.get("foulsPerMatch"),
                "foulsWonPerMatch": long_run.get("foulsWonPerMatch"),
                "cardsPerMatch": long_run.get("cardsPerMatch"),
                "rateMatches": long_run.get("played", 0),
            }
        )

    for row in table:
        club = row["team"]
        squad = None
        if by_fpl and to_fpl:
            try:
                squad = by_fpl.get(to_fpl(club))
            except Exception:
                squad = None
        squads[club] = squad
        row["players"] = _players(history, history_name(club), squad)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "seasons": labels,
        "tableSeason": table_season,
        "tablePlayed": int(current_matches.shape[0]),
        "rateSeasons": " and ".join(labels),
        "table": table,
    }


def publish(output: Path = OUTPUT) -> dict:
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")))
    return payload


if __name__ == "__main__":
    r = publish()
    print(f"{len(r['table'])} clubs, seasons {', '.join(r['seasons'])}\n")
    print(f"table: {r['tableSeason']}   rates: {r['rateSeasons']}\n")
    print(f"{'#':<3}{'club':<18}{'pl':>4}{'pts':>5}{'fouls':>8}{'won':>7}{'cards':>7}{'players':>9}")
    print("-" * 62)
    for i, t in enumerate(r["table"][:8], 1):
        print(f"{i:<3}{t['team']:<18}{t['played']:>4}{t['points']:>5}"
              f"{t['foulsPerMatch'] or 0:>8}{t['foulsWonPerMatch'] or 0:>7}"
              f"{t['cardsPerMatch'] or 0:>7}{len(t['players']):>9}")
