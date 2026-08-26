"""The two domestic cups, as pages of raw record plus one honest model number.

Replaces publish/cup.py. Three things changed and each has a reason.

**The slate builds itself.** It came from data/cup_fixtures.json by hand, which
meant somebody had to notice a tie and type it in. sources/cup_slate pulls both
cups from API-Football and keeps whichever ties have two clubs we hold history
for, which is 44 of the 92 league clubs and almost none of a third round.

**Championship clubs are in, and they change what may be published.** No
player-level foul data exists for the second tier at any price. So a tie with
one gets its raw team record, the referee's record, the pairing's history and
an expected match total, and it never gets a player pick. `kind` carries that
decision from the slate through to the page, and `_stats_only` is what enforces
it: the player payload is not merely omitted, it is never built.

**The two cups are separate pages.** The old '-cup' suffix put Arsenal v
Chelsea in the FA Cup and the same pairing in the League Cup on one URL.

Still exhibition, still recorded nowhere. No claims, no slates, no league
scoring, no track-record noise from games our results source will never grade.
The contract is a league of Premier League gameweeks (docs/38) and a cup night
is not quietly a fourth bet in it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from foulgorithm.identity.teams import has_player_data
from foulgorithm.sources import cup_slate
from foulgorithm.stats import comparison, cup_head_to_head, referee_record, team_record

OUTPUT_DIR = Path("site/public/data")

#: Slug fragment to output file. One cup, one file, one page.
FILES = {"FA Cup": "fa-cup.json", "League Cup": "league-cup.json"}


def build(
    ties: list[dict],
    matches: list[dict],
    baselines: dict[str, dict],
    rates: dict[str, dict],
    competition: str | None = None,
    totals: dict[str, dict] | None = None,
    lineups: dict[str, dict] | None = None,
    sheets: dict[str, dict] | None = None,
    now: datetime | None = None,
) -> dict:
    """One cup's payload. Pure: everything it needs is passed in."""
    now = now or datetime.now(timezone.utc)
    totals = totals or {}
    lineups = lineups or {}
    sheets = sheets or {}

    if competition:
        ties = [t for t in ties if t["competition"] == competition]

    return {
        "generatedAt": now.replace(microsecond=0).isoformat(),
        "competition": competition or (ties[0]["competition"] if ties else None),
        # Said out loud in the payload, not just in a docstring. Exhibition
        # means nothing here is graded, scored or carried into the record.
        "recorded": False,
        "ties": [
            _tie(t, matches, baselines, rates, totals, lineups, sheets) for t in ties
        ],
    }


def _tie(tie, matches, baselines, rates, totals, lineups, sheets) -> dict:
    home, away = tie["home_team_raw"], tie["away_team_raw"]

    # The CLUB LIST is the authority on what may be published, never the label
    # the slate attached. If a tie arrives marked 'full' with a Championship
    # club in it, it is downgraded here and its house sheet is dropped, because
    # no player-level foul data exists for that club at any price.
    kind = tie["kind"] if has_player_data(home) and has_player_data(away) else "total"
    sheet = sheets.get(tie["slug"]) if kind == "full" else None
    hr = team_record.build(home, matches)
    ar = team_record.build(away, matches)

    block = {
        "slug": tie["slug"],
        "competition": tie["competition"],
        "round": tie.get("round"),
        "home": home,
        "away": away,
        "kickoff": tie["kickoff_utc"].isoformat(),
        # 'full' means both clubs are Premier League and the player model may
        # run. 'total' means at least one is a Championship club, where the
        # only model number allowed is the match total. See sources/cup_slate.
        "kind": kind,
        "referee": _referee(tie, matches, home, away),
        # The league's API names the official at kickoff, not before, so most
        # ties are published without one. Flagged rather than left to a blank
        # space: "not appointed yet" and "nothing on this official" look the
        # same on a page and are not the same claim.
        "refereePending": tie.get("referee_raw") is None,
        "compare": comparison.build(hr, ar, baselines, rates),
        "crossDivision": comparison.cross_division_note(hr, ar),
        "record": {
            "home": _side(hr),
            "away": _side(ar),
        },
        "headToHead": _head_to_head(home, away, matches),
        "houseSheet": sheet,
        "total": totals.get(tie["slug"]),
        "lineups": _lineups(lineups, home, away),
    }
    return block


def _side(record) -> dict:
    """A club's sample, said plainly. The spell label is the important part.

    "38 in the Premier League, 8 in the Championship" is the difference between
    a pooled number a reader can trust and one that quietly mixes two leagues.
    """
    return {
        "team": record.team,
        "matches": record.matches,
        "spell": record.spell_label() if record.spells else None,
        "division": record.division,
        "crossedDivisions": record.crossed_divisions,
    }


def _referee(tie, matches, home, away) -> dict | None:
    record = referee_record.build(tie.get("referee_raw"), matches)
    if record is None:
        return None
    return {
        "referee": tie.get("referee_display") or record.referee,
        "matches": record.matches,
        "foulsPerMatch": record.fouls_per_match,
        "cardsPerMatch": record.cards_per_match,
        "cardsPerFoul": record.cards_per_foul,
        "thin": record.thin,
        "clubs": {
            side: {
                "matches": record.club(club).matches,
                "foulsPerMatch": record.club(club).fouls_per_match,
                "yellowsPerMatch": record.club(club).yellows_per_match,
            }
            for side, club in (("home", home), ("away", away))
        },
        # Carried onto the page, not left in a docstring. A referee's fouls per
        # match is not a referee effect: one handed more derbies shows more of
        # everything without being any stricter.
        "note": "Observations, not a referee effect. A referee given more "
                "derbies shows more of everything without being stricter. "
                "Cards per foul is the column worth reading.",
    }


def _lineups(lineups: dict, home: str, away: str) -> dict | None:
    """The two confirmed elevens, as names.

    `lineups` arrives keyed "{team}|{home} v {away}", which is the shape both
    the league feed and API-Football are reshaped into, so a tie picks out its
    own two entries and cannot pick up anybody else's.

    Names only, deliberately. A Premier League eleven could carry each player's
    foul rate and a Championship one could not, and showing rates on one side
    would make the tie asymmetric in exactly the way the rest of the page
    refuses to be.
    """
    label = f"{home} v {away}"

    def side(team):
        sheet = lineups.get(f"{team}|{label}")
        if sheet is None:
            return None
        return {
            "team": team,
            "formation": getattr(sheet, "formation", None),
            "starters": list(getattr(sheet, "starters", []) or []),
        }

    found = {"home": side(home), "away": side(away)}
    return found if any(found.values()) else None


def _head_to_head(home, away, matches) -> dict:
    h2h = cup_head_to_head.build(home, away, matches)
    return {
        "meetings": h2h.meetings,
        "rows": h2h.rows,
        "fouls": h2h.fouls,
        "totalFouls": h2h.total_fouls,
    }


def write(payload: dict, output_dir: Path = OUTPUT_DIR) -> Path:
    competition = payload["competition"]
    name = FILES.get(competition)
    if name is None:
        raise ValueError(f"no output file for competition {competition!r}")
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return path


def publish(
    output_dir: Path = OUTPUT_DIR,
    lineups: dict | None = None,
    now: datetime | None = None,
) -> dict[str, dict]:
    """Pull both cups, build both pages, write both files.

    Returns the payloads by competition. An empty cup still writes a file: a
    page that says "no ties on the slate" is honest, and a stale file from
    three weeks ago is not.
    """
    from foulgorithm.features import promotion
    from foulgorithm.identity.teams import CHAMPIONSHIP_CLUBS, PREMIER_LEAGUE_CLUBS
    from foulgorithm.stats import history as stats_history
    from foulgorithm.stats import league_baseline

    now = now or datetime.now(timezone.utc)

    try:
        ties = cup_slate.fetch(now=now)
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        print(f"  cup slate unavailable: {exc}")
        ties = []
    print(f"  {len(ties)} ties on the slate we hold both clubs for")

    by_division = stats_history.window()
    matches = stats_history.pooled(by_division)
    baselines = {d: league_baseline.build(rows) for d, rows in by_division.items()}
    rates = _division_rates(matches, PREMIER_LEAGUE_CLUBS, CHAMPIONSHIP_CLUBS)

    totals = _totals(ties)
    sheets = _house_sheets([t for t in ties if t["kind"] == "full"], lineups)

    out = {}
    for competition in FILES:
        payload = build(
            ties, matches, baselines, rates,
            competition=competition, totals=totals, lineups=lineups,
            sheets=sheets, now=now,
        )
        path = write(payload, output_dir)
        print(f"  {competition}: {len(payload['ties'])} ties -> {path}")
        out[competition] = payload
    return out


def _division_rates(matches, premier, championship) -> dict[str, dict]:
    """Every club's rate per stat per division, for the within-division ranks."""
    from foulgorithm.stats.comparison import BLOCKS

    fields = [attr for _, rows in BLOCKS for attr, _, _ in rows]
    out: dict[str, dict] = {}
    for division, clubs in (("E0", premier), ("E1", championship)):
        table: dict[str, dict[str, float]] = {f: {} for f in fields}
        for club in clubs:
            record = team_record.build(club, matches)
            # A club three games into a season has a rate that is noise, and a
            # rank built on noise reads as a fact. Ten matches is the same
            # floor features/promotion uses for exactly this reason.
            if record.matches < 10:
                continue
            for f in fields:
                value = getattr(record, f)
                if value is not None:
                    table[f][club] = value
        out[division] = table
    return out


def _totals(ties: list[dict]) -> dict[str, dict]:
    """Expected match fouls per tie. The one model number a cup page carries.

    Every tie gets one, including Premier League ties: a total is a total, and
    the page reads the same either way. Cross-division ties route through
    CupTotal, which puts a second-tier club's own record on the top-flight
    scale rather than letting it default to the league average.
    """
    if not ties:
        return {}

    import pandas as pd

    from foulgorithm.markets import base as markets
    from foulgorithm.models.cup_totals import CupTotal
    from foulgorithm.store.matches import load_matches

    try:
        model = CupTotal()
        model.fit(load_matches())
    except Exception as exc:  # noqa: BLE001
        print(f"  no match totals this run: {exc}")
        return {}

    frame = pd.DataFrame([
        {
            "home_team_raw": t["home_team_raw"],
            "away_team_raw": t["away_team_raw"],
            "kickoff_utc": pd.Timestamp(t["kickoff_utc"]),
            "referee_raw": t["referee_raw"],
            "odds_home": None, "odds_draw": None, "odds_away": None,
        }
        for t in ties
    ])

    spec = markets.get("match_total_fouls")
    out = {}
    for tie, (_, row), dist in zip(ties, frame.iterrows(), model.predict(frame), strict=True):
        unpriced = model.unknown(row)
        out[tie["slug"]] = {
            "expectedFouls": round(dist.mean(), 2),
            "lines": [
                {
                    "line": line,
                    "probOver": round(dist.prob_over(line), 4),
                    "fairOddsOver": round(dist.fair_odds_over(line), 2),
                }
                for line in spec.lines
            ],
            # Said out loud. A club we could not price falls back to the league
            # average, which is the honest floor, but a reader has to know that
            # is what happened or the number reads as a view on the club.
            "unpriced": unpriced,
            "crossDivision": tie["kind"] == "total",
            "note": "Cup elevens are rotated, so this is the clubs' league "
                    "behaviour applied to a game they may not pick a league "
                    "side for.",
        }
    return out


def _house_sheets(full_ties: list[dict], lineups: dict | None) -> dict[str, dict]:
    """Player picks, for Premier League ties only.

    Runs the same engine the league round runs, on the same exhibition footing
    publish/cup.py used: record=False, so the payload and pages are written but
    nothing enters the append-only stores and nothing is graded or scored.
    """
    if not full_ties:
        return {}

    from foulgorithm.publish import player_round

    try:
        payload = player_round.publish(
            output=OUTPUT_DIR / "cup-players.json",
            fixtures_override=[_engine_row(t) for t in full_ties],
            record=False,
            competition="cup",
            lineups_override=lineups,
            lineups_source="API-Football",
        )
    except Exception as exc:  # noqa: BLE001 - a cup problem never takes the page down
        print(f"  no house sheets this run: {exc}")
        return {}

    by_label = {
        f"{f['home']} v {f['away']}": f.get("houseSheet")
        for f in payload.get("board", [])
    }
    return {
        t["slug"]: sheet
        for t in full_ties
        if (sheet := by_label.get(f"{t['home_team_raw']} v {t['away_team_raw']}"))
    }


def _engine_row(tie: dict) -> dict:
    """A slate row in the shape features/next_round.fetch returns."""
    return {
        "home_team_raw": tie["home_team_raw"],
        "away_team_raw": tie["away_team_raw"],
        "kickoff_utc": tie["kickoff_utc"],
        "known_at": tie["known_at"],
        "referee_raw": tie["referee_raw"],
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
        "source": tie["source"],
        "competition": tie["competition"],
    }


if __name__ == "__main__":
    publish()
