"""The stats sheet. What happened, with no model anywhere near it.

Built for the reader who wants the numbers handed to them and would rather reach
their own conclusion than be told what to back. Every figure is an average or a
count taken from history. **Nothing on this page is predicted**, and a test
enforces that, because the whole value of it is that a reader can check any
number against a scoreboard.

Hit rates carry the recent form. "Over 15.5 fouls, four of the last five" is a
fact someone can verify. A probability is something they can only take on trust.

Lines are chosen from the data rather than picked. A line nothing ever clears
produces five identical dots and tells the reader nothing, so each one sits at
the median of its own series, where the dots carry the most information.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUTPUT = Path("site/public/data/matchday.json")

WINDOW = 5           # matches shown as dots
FORM_SEASONS = 2     # how far back the averages look
TOP_PLAYERS = 6

# Real playing time, not appearances. Three appearances of nine minutes is a
# third of a match, and a per-90 rate off that is noise dressed as a number.
MIN_NINETIES = 4.0

# Team averages, mirrored on both sides of the sheet. Order is the display order.
TEAM_METRICS = [
    ("foulsFor", "Fouls committed", "fouls", "for"),
    ("foulsAgainst", "Fouls won", "fouls", "against"),
    ("cardsFor", "Cards shown", "yellows", "for"),
    ("cardsAgainst", "Cards drawn", "yellows", "against"),
    ("shotsFor", "Shots", "shots", "for"),
    ("shotsAgainst", "Shots faced", "shots", "against"),
    ("cornersFor", "Corners", "corners", "for"),
    ("cornersAgainst", "Corners faced", "corners", "against"),
]


def hits(values: list[float], line: float) -> list[bool]:
    """Did each value clear the line. Half-lines only, so there is never a push."""
    return [v > line for v in values]


def line_for(values: list[float]) -> float | None:
    """A half-line just under the median, where the dots say most.

    Just UNDER rather than just over, so the median match counts as a hit. A
    league averaging 12 fouls gets a line of 11.5, which is how these sheets are
    normally read, and it keeps hit rates near half rather than under it.

    Floored at 0.5, because "over -0.5" always hits and five identical dots
    carry no information at all.
    """
    if not values:
        return None
    return max(round(statistics.median(values)) - 0.5, 0.5)


def hit_rate(values: list[float], line: float, window: int = WINDOW) -> dict:
    """The last `window` results against a line, most recent first.

    Reports `n` as well as the dots. Drawing five dots from three matches would
    overstate the evidence, and an empty run reads as "never happened", which is
    a claim rather than an absence.
    """
    recent = list(reversed(values))[:window]
    marks = hits(recent, line)
    return {
        "line": line,
        "hits": marks,
        "n": len(marks),
        "rate": round(sum(marks) / len(marks), 3) if marks else None,
    }


def _team_series(matches: pd.DataFrame, team: str) -> dict[str, list[float]]:
    """Per-match values for one club, oldest first, both venues pooled."""
    out: dict[str, list[float]] = {}
    rows = matches[
        (matches["home_team_raw"] == team) | (matches["away_team_raw"] == team)
    ].sort_values("kickoff_utc")

    for _, row in rows.iterrows():
        side = "home" if row["home_team_raw"] == team else "away"
        other = "away" if side == "home" else "home"
        for _, _, stat, direction in TEAM_METRICS:
            source = side if direction == "for" else other
            value = row.get(f"{source}_{stat}")
            if value is not None and not pd.isna(value):
                out.setdefault(f"{stat}_{direction}", []).append(float(value))
    return out


def _league_ranks(matches: pd.DataFrame, clubs: list[str] | None = None) -> dict:
    """Every club's rank on every mirrored metric, most first.

    Computed once per sheet so each club's average can carry its context
    ("3 of 20") where the reader is already looking. Rank 1 is the highest
    value: most fouls is not worse, it is just most, and which end a reader
    wants depends on what they came for. `clubs` restricts the ranking to
    the current league: the match window spans two seasons, and without the
    restriction relegated clubs pad the field to "18 of 23".
    """
    pool = sorted(
        set(matches["home_team_raw"].dropna()) | set(matches["away_team_raw"].dropna())
    )
    clubs = sorted(set(clubs) & set(pool)) if clubs is not None else pool
    means: dict[str, dict[str, float]] = {}
    for club in clubs:
        series = _team_series(matches, club)
        for key, _, stat, direction in TEAM_METRICS:
            values = series.get(f"{stat}_{direction}", [])
            if values:
                means.setdefault(key, {})[club] = statistics.fmean(values)

    by_metric: dict[str, dict[str, int]] = {}
    for key, per_club in means.items():
        ordered = sorted(per_club, key=lambda c: -per_club[c])
        by_metric[key] = {club: i + 1 for i, club in enumerate(ordered)}
    return {"clubs": len(clubs), "byMetric": by_metric}


def _team_block(
    matches: pd.DataFrame,
    team: str,
    second_tier: pd.DataFrame | None = None,
    ranks: dict | None = None,
) -> dict:
    """One club's averages and recent form.

    A promoted club has no top-flight history and would otherwise show an empty
    column. On a page whose whole claim is "this is what happened", its
    Championship record IS what happened, so it is used and labelled as such
    rather than left blank. The reader can discount it themselves, which is the
    entire point of a stats sheet.

    Note this is the opposite call from the model, which shrinks a promoted
    club's second-tier deviation by 63% because only 37% of it survives
    promotion. That correction belongs to a forecast. This page is not one.
    """
    series = _team_series(matches, team)
    division = "Premier League"
    if not any(series.values()) and second_tier is not None:
        series = _team_series(second_tier, team)
        division = "Championship" if any(series.values()) else division

    averages, form = {}, {}
    for key, label, stat, direction in TEAM_METRICS:
        values = series.get(f"{stat}_{direction}", [])
        averages[key] = {
            "label": label,
            "value": round(statistics.fmean(values), 2) if values else None,
            "matches": len(values),
        }
        # Rank context, top-flight records only: ranking a Championship
        # average against Premier League ones would compare across leagues.
        rank = (
            ((ranks or {}).get("byMetric") or {}).get(key, {}).get(team)
            if division == "Premier League"
            else None
        )
        if rank is not None:
            averages[key]["rank"] = rank
            averages[key]["rankOf"] = (ranks or {}).get("clubs")
        line = line_for(values)
        form[key] = hit_rate(values, line) if line is not None else None
    return {"averages": averages, "form": form, "division": division}


def _referee_block(name: str | None, matches: pd.DataFrame) -> dict:
    """A referee's own numbers. Raw averages, and the confounding is stated.

    These are NOT a referee effect. A referee assigned to more derbies will show
    more cards without being stricter, and separating the two needs a model. The
    site says so where this is rendered.
    """
    empty = {
        "name": name,
        "matches": 0,
        "foulsPerMatch": None,
        "yellowsPerMatch": None,
        "redsPerMatch": None,
        "foulsVsLeague": None,
        "foulsBooked": None,
    }
    if not name:
        return empty

    rows = matches[matches["referee_raw"] == name]
    if rows.empty:
        return empty

    def per_match(a: str, b: str) -> float:
        return round(float((rows[a].fillna(0) + rows[b].fillna(0)).mean()), 2)

    fouls = per_match("home_fouls", "away_fouls")
    league_fouls = float((matches["home_fouls"].fillna(0) + matches["away_fouls"].fillna(0)).mean())
    cards = float(
        rows[["home_yellows", "away_yellows", "home_reds", "away_reds"]]
        .fillna(0)
        .sum(axis=1)
        .mean()
    )

    return {
        "name": name,
        "matches": int(len(rows)),
        "foulsPerMatch": fouls,
        "yellowsPerMatch": per_match("home_yellows", "away_yellows"),
        "redsPerMatch": per_match("home_reds", "away_reds"),
        # The two numbers a reader acts on, from the retired referees page:
        # how he sits against the league, and what share of fouls he books.
        "foulsVsLeague": round((fouls / league_fouls - 1) * 100) if league_fouls else None,
        "foulsBooked": round(cards / fouls * 100) if fouls else None,
    }


def _players(
    history: pd.DataFrame,
    team: str,
    opponents: list[str],
    squad: set[str] | None = None,
) -> dict:
    """Two tables per club: who concedes fouls, and who wins them.

    `squad` restricts the tables to the club's CURRENT players. Without it the
    sheet lists whoever appeared in the window, which puts players who left a
    year ago at the top of a page about Saturday. That is the stale-squad bug
    the model already fixed once, and it should not come back on a new page.

    `opponents` names the other side's most foul-drawing players, which is as
    close as we can honestly get to the "likely opponent" column these sheets
    carry. A real positional matchup needs formation and tracking data we do not
    hold, so this is who a defender is most likely to have trouble with, not who
    he will actually mark.
    """
    rows = history[history["team"] == team]
    if squad is not None:
        rows = rows[rows["player"].isin(squad)]
    if rows.empty:
        return {"defensive": [], "offensive": []}

    grouped = rows.groupby("player")
    stats = pd.DataFrame(
        {
            "matches": grouped.size(),
            "minutes": grouped["minutes"].mean(),
            "nineties": grouped["minutes"].sum() / 90.0,
            "fouls": grouped["fouls_committed"].sum(),
            "won": grouped["fouls_drawn"].sum(),
            "tackles": grouped["tackles_won"].sum(),
            "yellows": grouped["yellows"].sum(),
        }
    )
    stats = stats[stats["nineties"] >= MIN_NINETIES]
    if stats.empty:
        return {"defensive": [], "offensive": []}

    for column, source in (("foulsPer90", "fouls"), ("wonPer90", "won"), ("tacklesPer90", "tackles")):
        stats[column] = stats[source] / stats["nineties"]

    def per_player_hits(player: str, column: str, line: float) -> dict:
        values = rows[rows["player"] == player].sort_values("kickoff_utc")[column].tolist()
        return hit_rate([float(v) for v in values], line)

    defensive = []
    for player, r in stats.sort_values("foulsPer90", ascending=False).head(TOP_PLAYERS).iterrows():
        defensive.append(
            {
                "player": player,
                "matches": int(r["matches"]),
                "minutes": round(float(r["minutes"])),
                "foulsPer90": round(float(r["foulsPer90"]), 2),
                "tacklesPer90": round(float(r["tacklesPer90"]), 2),
                "yellows": int(r["yellows"]),
                "form": per_player_hits(player, "fouls_committed", 0.5),
                "watch": opponents[:2],
            }
        )

    offensive = []
    for player, r in stats.sort_values("wonPer90", ascending=False).head(TOP_PLAYERS).iterrows():
        offensive.append(
            {
                "player": player,
                "matches": int(r["matches"]),
                "minutes": round(float(r["minutes"])),
                "wonPer90": round(float(r["wonPer90"]), 2),
                "form": per_player_hits(player, "fouls_drawn", 0.5),
                "formTwo": per_player_hits(player, "fouls_drawn", 1.5),
                "watch": opponents[:2],
            }
        )
    return {"defensive": defensive, "offensive": offensive}


def _foul_winners(history: pd.DataFrame, team: str, squad: set[str] | None = None) -> list[str]:
    rows = history[history["team"] == team]
    if squad is not None:
        rows = rows[rows["player"].isin(squad)]
    if rows.empty:
        return []
    grouped = rows.groupby("player")
    nineties = grouped["minutes"].sum() / 90.0
    per90 = grouped["fouls_drawn"].sum() / nineties
    return list(per90[nineties >= MIN_NINETIES].sort_values(ascending=False).head(3).index)


def _current_squads(history: pd.DataFrame) -> dict[str, set[str]]:
    """Each club's current players, in history spelling, from the league's own data.

    Returns an empty mapping if the squad source is unavailable, and the caller
    then shows every player in the window rather than nothing. A stale table is
    worse than a fresh one and better than a blank page, and the source is named
    on the page either way.
    """
    try:
        from foulgorithm.identity import players as identity
        from foulgorithm.identity.teams import to_fpl
        from foulgorithm.sources import fpl

        squads = fpl.current_squads()
        everyone = [p for club in squads.values() for p in club]
        resolution = identity.resolve(everyone, history["player"].unique())
        by_fpl_club = {
            club: {resolution.matched[p.name] for p in members if p.name in resolution.matched}
            for club, members in squads.items()
        }
        return {"__fpl__": by_fpl_club, "__to_fpl__": to_fpl}  # type: ignore[return-value]
    except Exception:
        return {}


def build(seasons: int = FORM_SEASONS) -> dict:
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

    second = []
    for label in labels:
        try:
            second.append(pd.DataFrame(football_data.parse(football_data.fetch(label, division="E1"))))
        except Exception:
            continue
    championship = pd.concat(second, ignore_index=True) if second else pd.DataFrame()

    history = load_player_matches()
    cutoff = history["kickoff_utc"].max() - pd.Timedelta(days=400 * seasons)
    history = history[history["kickoff_utc"] >= cutoff]

    fixtures = pd.DataFrame(football_data.fetch_fixtures())
    league_ranks = _league_ranks(
        matches,
        clubs=sorted(
            set(fixtures["home_team_raw"].dropna()) | set(fixtures["away_team_raw"].dropna())
        ),
    )
    lookup = _current_squads(history)
    by_club, to_fpl = lookup.get("__fpl__"), lookup.get("__to_fpl__")

    def squad_for(team: str) -> set[str] | None:
        if not by_club or not to_fpl:
            return None
        try:
            return by_club.get(to_fpl(team))
        except Exception:
            return None

    out = []
    for fx in fixtures.itertuples():
        home, away = fx.home_team_raw, fx.away_team_raw
        squads_here = {side: squad_for(side) for side in (home, away)}
        winners = {
            side: _foul_winners(history, history_name(side), squads_here[side])
            for side in (home, away)
        }
        out.append(
            {
                "home": home,
                "away": away,
                "kickoff": fx.kickoff_utc.isoformat(),
                "referee": _referee_block(fx.referee_raw, matches),
                "teams": {
                    home: {
                        **_team_block(matches, home, championship, ranks=league_ranks),
                        "players": _players(
                            history, history_name(home), winners[away], squads_here[home]
                        ),
                    },
                    away: {
                        **_team_block(matches, away, championship, ranks=league_ranks),
                        "players": _players(
                            history, history_name(away), winners[home], squads_here[away]
                        ),
                    },
                },
            }
        )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "window": WINDOW,
        "seasons": labels,
        "note": (
            "Averages and hit rates from completed matches. Nothing here is "
            "forecast; every number can be checked against a scoreboard."
        ),
        "fixtures": out,
    }


def publish(output: Path = OUTPUT) -> dict:
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")))
    return payload


if __name__ == "__main__":
    result = publish()
    print(f"{len(result['fixtures'])} fixtures, seasons {', '.join(result['seasons'])}")
    for f in result["fixtures"][:3]:
        ref = f["referee"]
        print(f"\n{f['home']} v {f['away']}   ref {ref['name']} "
              f"({ref['foulsPerMatch']} fouls, {ref['yellowsPerMatch']} cards over {ref['matches']})")
        for side in (f["home"], f["away"]):
            a = f["teams"][side]["averages"]
            form = f["teams"][side]["form"]["foulsFor"]
            dots = "".join("O" if h else "." for h in form["hits"]) if form else ""
            div = f["teams"][side]["division"]
            tag = "" if div == "Premier League" else f"  [{div}]"
            print(f"  {side:<16}fouls {a['foulsFor']['value']}  won {a['foulsAgainst']['value']}  "
                  f"cards {a['cardsFor']['value']}   over {form['line'] if form else '?'}: {dots}{tag}")
