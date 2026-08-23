"""Publish player predictions and each character's picks for the next matchday.

Two outputs in one file:
  - the full board, every player in every fixture, both markets
  - five picks per character, chosen in that character's temperament
"""

from __future__ import annotations

import json
from functools import lru_cache
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from foulgorithm.characters import base as characters
from foulgorithm.publish import combinations as combos
from foulgorithm.identity import players as identity
from foulgorithm.identity.teams import history_name, to_fpl
from foulgorithm.markets import odds as odds_math
from foulgorithm.models import calibration, involvement, player_models as pm
from foulgorithm.sources import football_data, fpl, league_stats
from foulgorithm.sources.lineups import for_round as confirmed_lineups
from foulgorithm.store import predictions as pred_store
from foulgorithm.store.players import load_player_matches

OUTPUT = Path("site/public/data/players.json")

# Below this, the player is mostly the league prior and we say so.
THIN_EVIDENCE = 8.0
# Required edge over fair odds before we publish a price floor. Fair odds are
# break-even, so backing at exactly fair returns nothing in expectation.
EDGE_MARGIN = 0.10
# Each character publishes this many picks per matchday.
PICKS_PER_CHARACTER = 5

# Odds tiers. Every character builds a slip at EACH target, so the five are
# compared at matched risk rather than at whatever risk their temperament
# happened to produce. A cautious character can no longer look better simply
# by picking near-certainties, and a bold one cannot look better by reaching.
#
# The targets are OUR fair odds, not anyone's price. We hold no bookmaker odds
# for these markets and, per the research, no archive of them exists to buy.
# DECIMAL prices, and the labels derived from them rather than assumed. These
# are 2/1, 3/1, 5/1, 10/1 and 20/1 fractional. Held as (2.0, 3.0, 5.0, 10.0)
# they were rendered "2/1", "3/1" and so on, which made every published tier one
# step longer than it read. See foulgorithm.markets.odds.
ODDS_TIERS = (3.0, 4.0, 6.0, 11.0, 21.0)
MAX_LEGS_PER_TIER = 6

# Pinned bands, UK PHIA yardstick. If we write a word it always means this range.
BANDS = [
    (0.90, "Almost certain"),
    (0.80, "Highly likely"),
    (0.55, "Likely"),
    (0.40, "Realistic possibility"),
    (0.25, "Unlikely"),
    (0.10, "Highly unlikely"),
    (0.00, "Remote chance"),
]


def band(p: float) -> str:
    for threshold, word in BANDS:
        if p >= threshold:
            return word
    return "Remote chance"


@dataclass(frozen=True)
class Selection:
    """A player we expect to feature, and the history we can attach to him."""

    display: str          # what to show, e.g. "Saka"
    full: str             # the squad-list name, e.g. "Bukayo Saka"
    history: str | None   # the name his foul record is filed under, if resolved
    position: str
    available: bool
    news: str
    confirmed: bool = False

    @property
    def lookup(self) -> str:
        """The name to ask the model about. Unresolved players get a position prior."""
        return self.history or self.full


def squad(
    squads,
    resolution,
    team: str,
    limit: int = 16,
    lineup=None,
    history=None,
    as_of=None,
) -> list[Selection]:
    """Who is likely to feature, from the CURRENT squad list.

    Previously derived from foul history ending September 2025, which named
    players who had since transferred and missed every summer signing. Now the
    squad comes from the league's own live data and only the RATES come from
    history.

    Before a confirmed eleven exists, the guess leads with whoever started the
    club's LAST match rather than with a season-long start count. Measured over
    1,058 team-matches that is 76.5% against 63.1%, and topping it up from the
    count where the last eleven is short reaches 78.1%. Anyone FPL flags injured
    or suspended is removed either way.
    """
    players = squads.get(to_fpl(team), [])

    # A confirmed eleven beats any prediction of one. When it exists, use it and
    # say so; the two are graded separately because they are different products.
    if lineup and lineup.starters:
        by_key = {fpl.normalise(p.name): p for p in players}
        out = []
        for name in lineup.starters:
            match = by_key.get(fpl.normalise(name))
            out.append(
                Selection(
                    display=match.web_name if match else name.split()[-1],
                    full=match.name if match else name,
                    history=resolution.matched.get(match.name) if match else None,
                    position=match.position if match else "?",
                    available=True,
                    news="",
                    confirmed=True,
                )
            )
        return out

    ranked = fpl.likely_eleven(players, limit)

    # Lead with the last eleven where we can. It is a fifteen-point better
    # predictor than a season's start count and costs nothing.
    if history is not None and as_of is not None:
        from foulgorithm.features import expected_xi
        from foulgorithm.identity.teams import history_name

        started = expected_xi.last_eleven(history, history_name(team), as_of)
        if started:
            by_history = {
                resolution.matched.get(p.name): p for p in players if p.name in resolution.matched
            }
            unavailable = {
                by_history[h].name
                for h in started
                if h in by_history and not by_history[h].available
            }
            lead = [
                by_history[h]
                for h in started
                if h in by_history and by_history[h].name not in unavailable
            ]
            seen = {p.name for p in lead}
            ranked = lead + [p for p in ranked if p.name not in seen]
            ranked = ranked[:limit]

    out = []
    for p in ranked:
        out.append(
            Selection(
                display=p.web_name,
                full=p.name,
                history=resolution.matched.get(p.name),
                position=p.position,
                available=p.available,
                news=p.news,
                confirmed=False,
            )
        )
    return out


@lru_cache(maxsize=1)
def _pairing_history(seasons: int = 12) -> pd.DataFrame:
    """Recent completed seasons of match results, for the head-to-head table."""
    from foulgorithm.publish.site_export import season_labels

    frames = []
    for label in season_labels()[-seasons:]:
        try:
            frames.append(pd.DataFrame(football_data.parse(football_data.fetch(label))))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["known_at"] = pd.to_datetime(out["known_at"], utc=True)
    return out


def publish(output: Path = OUTPUT) -> dict:
    history = load_player_matches()
    fixtures = pd.DataFrame(football_data.fetch_fixtures())
    as_of = datetime.now(timezone.utc)

    try:
        lineups = confirmed_lineups()
    except Exception as exc:  # noqa: BLE001 - reported, never silently empty
        print(f"  confirmed lineups unavailable: {exc}")
        lineups = {}

    squads = fpl.current_squads()
    everyone = [p for club in squads.values() for p in club]
    resolution = identity.resolve(everyone, history["player"].unique())

    committed = {c: pm.build(c, "player_fouls_committed") for c in pm.CHARACTER_SETTINGS}
    drawn = {c: pm.build(c, "player_fouls_drawn") for c in pm.CHARACTER_SETTINGS}

    # Only Valentina reads this, and only she stores it. See her method in
    # foulgorithm.features.head_to_head.
    #
    # Built from completed seasons, not the current one. A pairing effect needs
    # a run of meetings to say anything, and the current season file does not
    # exist until that season is underway.
    for model in (*committed.values(), *drawn.values()):
        model.fit_pairings(_pairing_history(), as_of)
    for model in list(committed.values()) + list(drawn.values()):
        model.fit(history)

    house_c, house_d = committed[HOUSE_MODEL], drawn[HOUSE_MODEL]

    board = []
    all_rows: list[dict] = []

    for fx in fixtures.itertuples():
        fixture_block = {
            "key": f"{fx.home_team_raw}-{fx.away_team_raw}",
            "home": fx.home_team_raw,
            "away": fx.away_team_raw,
            "kickoff": fx.kickoff_utc.isoformat(),
            "referee": fx.referee_raw,
            "lineupConfirmed": any(
                f"{t}|{fx.home_team_raw} v {fx.away_team_raw}" in lineups
                for t in (fx.home_team_raw, fx.away_team_raw)
            ),
            "teams": {},
        }
        for team, opponent in ((fx.home_team_raw, fx.away_team_raw), (fx.away_team_raw, fx.home_team_raw)):
            players = []
            label = f"{fx.home_team_raw} v {fx.away_team_raw}"
            for sel in squad(
                squads, resolution, team,
                lineup=lineups.get(f"{team}|{label}"),
                history=history, as_of=as_of,
            ):
                # A confirmed starter is a certainty, not a probability. Say so,
                # and the minutes mixture drops its unused branch entirely.
                state = "start" if sel.confirmed else None
                dist_c, why_c = house_c.predict_one(
                    sel.lookup, opponent, as_of, confirmed=state, team=team
                )
                dist_d, why_d = house_d.predict_one(
                    sel.lookup, opponent, as_of, confirmed=state, team=team
                )
                row = {
                    "player": sel.display,
                    "fullName": sel.full,
                    "position": sel.position,
                    "hasHistory": sel.history is not None,
                    "team": team,
                    "opponent": opponent,
                    "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
                    "kickoff": fx.kickoff_utc.isoformat(),
                    "expectedMinutes": why_c["expectedMinutes"],
                    "effectiveMatches": why_c["effectiveMatches"],
                    "thin": why_c["effectiveMatches"] < THIN_EVIDENCE or sel.history is None,
                    "committed": _market_block(dist_c, why_c, "player_fouls_committed"),
                    "drawn": _market_block(dist_d, why_d, "player_fouls_drawn"),
                }
                players.append(row)
                all_rows.append(row)
            fixture_block["teams"][team] = sorted(
                players, key=lambda r: -r["committed"]["p1plus"]
            )
        fixture_block["compare"] = _compare(history, fixture_block, as_of)
        fixture_block["summary"] = _summary(fixture_block)
        fixture_block["stats"] = {
            market: {
                team: [
                    {"player": r["player"], "value": round(r[market]["why"]["ratePer90"], 2)}
                    for r in sorted(
                        rows, key=lambda x: -x[market]["why"]["ratePer90"]
                    )[:8]
                ]
                for team, rows in fixture_block["teams"].items()
            }
            for market in ("committed", "drawn")
        }
        fixture_block["tickets"] = {
            market: [combos.serialise(t) for t in combos.best_tickets(fixture_block, market)]
            for market in ("committed", "drawn")
        }
        board.append(fixture_block)

    candidates, explorer = _candidate_table(
        squads, resolution, fixtures, committed, drawn, as_of, lineups, history
    )
    picks = [_character_picks(cid, candidates) for cid in pm.CHARACTER_SETTINGS]

    top = sorted(all_rows, key=lambda r: -r["committed"]["p1plus"])[:12]

    payload = {
        "generatedAt": as_of.replace(microsecond=0).isoformat(),
        "trainedOn": {
            "playerMatches": len(history),
            "players": int(history["player"].nunique()),
            "from": history["kickoff_utc"].min().strftime("%b %Y"),
            "to": history["kickoff_utc"].max().strftime("%b %Y"),
        },
        "edgeMargin": EDGE_MARGIN,
        "oddsTiers": list(ODDS_TIERS),
        "leagueLeaders": _league_leaders(),
        "calibration": {
            "committed3plus": calibration.factor("player_fouls_committed", 2.5),
            "drawn3plus": calibration.factor("player_fouls_drawn", 2.5),
            "note": "Probabilities are corrected for measured overconfidence "
                    "before publication. A factor of 1.0 would mean no correction "
                    "was needed.",
        },
        "squads": {
            "source": "Fantasy Premier League API",
            "players": len(everyone),
            "resolved": len(resolution.matched),
            "unresolved": len(resolution.unmatched),
        },
        "lineups": {
            "source": "Premier League API",
            "confirmed": len(lineups),
            "note": "Confirmed elevens appear about an hour before kickoff. "
                    "Until then these are predicted from current squads.",
        },
        "topFoulers": top,
        "board": board,
        "picks": picks,
        "fixtureSlips": _fixture_slips(candidates, fixtures),
        "formations": _formations(lineups),
        "explorer": {
            "models": list(pm.CHARACTER_SETTINGS),
            "lines": list(EXPLORER_LINES),
            "markets": list(EXPLORER_MARKETS),
            "house": HOUSE_MODEL,
            "rows": explorer,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    # Compact, not pretty. The scheduled jobs commit this file twice a week, so
    # indentation costs about half the repository's growth for no benefit that
    # a JSON viewer does not already give.
    output.write_text(json.dumps(payload, separators=(",", ":")))

    # Persist the claims themselves, separately from the page they render on.
    # The JSON above is a view and gets overwritten every run; this is the
    # record, and it is append-only.
    payload["recorded"] = _record(board, picks, as_of)
    return payload


def _record(board: list[dict], picks: list[dict], as_of) -> dict:
    """Write every published claim to the append-only store."""
    published = pred_store.now_iso()
    rows: list[pred_store.Prediction] = []

    for fixture in board:
        confirmed = bool(fixture.get("lineupConfirmed"))
        for players in fixture["teams"].values():
            for p in players:
                for market_key, block in (
                    ("player_fouls_committed", p["committed"]),
                    ("player_fouls_drawn", p["drawn"]),
                ):
                    for n in (1, 2, 3):
                        rows.append(
                            pred_store.Prediction(
                                published_at=published,
                                kickoff=fixture["kickoff"],
                                fixture=f"{fixture['home']} v {fixture['away']}",
                                entity=p.get("fullName") or p["player"],
                                market=market_key,
                                line=n - 0.5,
                                probability=block[f"p{n}plus"],
                                model_id="house",
                                model_version="1.0.0",
                                lineup_confirmed=confirmed,
                                thin=bool(p.get("thin")),
                                extra={"expectedMinutes": p["expectedMinutes"]},
                            )
                        )

    # Each character's tiered slips, so their record is gradeable too.
    for block in picks:
        for tier in block.get("tiers", []):
            for leg in tier["legs"]:
                rows.append(
                    pred_store.Prediction(
                        published_at=published,
                        kickoff=leg["kickoff"] if "kickoff" in leg else as_of.isoformat(),
                        fixture=leg["fixture"],
                        entity=leg.get("fullName") or leg["player"],
                        market=(
                            "player_fouls_committed"
                            if leg["market"] == "committed"
                            else "player_fouls_drawn"
                        ),
                        line=leg["line"],
                        probability=leg["prob"],
                        model_id=block["id"],
                        model_version="1.0.0",
                        lineup_confirmed=False,
                        thin=bool(leg.get("thin")),
                        extra={"tier": tier["target"]},
                    )
                )

    return pred_store.append(rows)


def _league_leaders() -> dict:
    """Current-season leaders. Context, not product, so a failure is survivable."""
    try:
        return league_stats.all_leaders(8)
    except Exception as exc:  # noqa: BLE001 - reported, never silently empty
        print(f"  league leaders unavailable: {exc}")
        return {}


def _summary(fixture: dict) -> dict:
    """What a compact fixture card needs, precomputed.

    The card should not have to scan every player to find its own headline.
    """
    everyone = [p for rows in fixture["teams"].values() for p in rows]
    if not everyone:
        return {}
    by_foul = sorted(everyone, key=lambda r: -r["committed"]["p1plus"])
    by_won = sorted(everyone, key=lambda r: -r["drawn"]["p1plus"])
    expected = sum(
        r["committed"]["why"]["ratePer90"] * r["expectedMinutes"] / 90.0
        for rows in fixture["teams"].values()
        for r in rows[:11]
    )
    return {
        "expectedFouls": round(expected, 1),
        "topFouler": {
            "player": by_foul[0]["player"],
            "team": by_foul[0]["team"],
            "outOf100": by_foul[0]["committed"]["outOf100"],
        },
        "topWinner": {
            "player": by_won[0]["player"],
            "team": by_won[0]["team"],
            "outOf100": by_won[0]["drawn"]["outOf100"],
        },
        "players": len(everyone),
    }


def _team_form(history: pd.DataFrame, team: str, as_of, days: int = 400) -> dict:
    """Recent team-level rates, for the head-to-head comparison."""
    past = history[(history["team"] == history_name(team)) & (history["known_at"] <= as_of)]
    if past.empty:
        return {}
    cutoff = past["kickoff_utc"].max() - pd.Timedelta(days=days)
    past = past[past["kickoff_utc"] >= cutoff]
    matches = past["kickoff_utc"].nunique()
    if not matches:
        return {}
    nineties = past["minutes"].sum() / 90.0
    return {
        "matches": int(matches),
        "foulsPerMatch": round(past["fouls_committed"].sum() / matches, 2),
        "foulsWonPerMatch": round(past["fouls_drawn"].sum() / matches, 2),
        "yellowsPerMatch": round(past["yellows"].fillna(0).sum() / matches, 2),
        "tacklesPerMatch": round(past["tackles_won"].fillna(0).sum() / matches, 2),
        "foulsPer90": round(past["fouls_committed"].sum() / max(nineties, 1e-6), 2),
    }


def _compare(history: pd.DataFrame, fixture: dict, as_of) -> dict:
    """Everything needed to render the two sides against each other.

    A mirrored table beats two separate ones: the reader compares by looking
    across a single row rather than by holding a number in their head while
    they find its opposite number in another table.
    """
    home, away = fixture["home"], fixture["away"]
    rows = []
    hf, af = _team_form(history, home, as_of), _team_form(history, away, as_of)

    for key, label, better in (
        ("foulsPerMatch", "Fouls committed per match", "high"),
        ("foulsWonPerMatch", "Fouls won per match", "high"),
        ("yellowsPerMatch", "Yellow cards per match", "high"),
        ("tacklesPerMatch", "Tackles won per match", "high"),
    ):
        h, a = hf.get(key), af.get(key)
        if h is None and a is None:
            continue
        # A promoted club has no top-flight history, which is a real fact rather
        # than a missing value. Show the side we know and mark the other, rather
        # than dropping the row and hiding that we know anything at all.
        rows.append(
            {
                "label": label,
                "home": h,
                "away": a,
                "higher": None if h is None or a is None else ("home" if h > a else "away"),
            }
        )

    # Model output for this fixture, on the same mirrored footing.
    players = fixture["teams"]
    for market, label in (("committed", "Expected fouls, XI"), ("drawn", "Expected fouls won, XI")):
        vals = {}
        for team, rowset in players.items():
            vals[team] = round(
                sum(r[market]["why"]["ratePer90"] * r["expectedMinutes"] / 90.0 for r in rowset[:11]),
                2,
            )
        if home in vals and away in vals:
            rows.append(
                {
                    "label": label,
                    "home": vals[home],
                    "away": vals[away],
                    "higher": "home" if vals[home] > vals[away] else "away",
                }
            )

    return {"rows": rows, "matches": {"home": hf.get("matches", 0), "away": af.get("matches", 0)}}


def _market_block(dist, why: dict, market: str = "player_fouls_committed") -> dict:
    out = {"why": why, "exact0": round(dist.pmf(0), 4)}
    for n in (1, 2, 3):
        # Correct known overconfidence before anything is published. The raw
        # number overstates the high lines, and it does so in the direction
        # that makes a bad bet look good.
        p = calibration.correct(dist.prob_over(n - 0.5), market, n - 0.5)
        out[f"p{n}plus"] = round(p, 4)
        out[f"fair{n}"] = round(1 / p, 2) if p > 0.001 else None
        out[f"floor{n}"] = round((1 / p) * (1 + EDGE_MARGIN), 2) if p > 0.001 else None
        out[f"band{n}"] = band(p)
    out["outOf100"] = round(out["p1plus"] * 100)
    return out


# Tayler is the house model: longest memory, heaviest shrinkage, never
# exaggerates. The one to quote when a single number is wanted.
HOUSE_MODEL = "tayler"

EXPLORER_LINES = (0.5, 1.5, 2.5, 3.5)
EXPLORER_MARKETS = ("committed", "drawn", "involvements")


def _candidate_table(squads, resolution, fixtures, committed, drawn, as_of, lineups, history=None):
    """Every candidate bet, with EVERY character's probability attached.

    Computed once, and returned alongside the explorer table so the predictions
    are made once rather than twice. Selection reads the candidates; the site's
    filterable view reads the explorer.

    Returns (candidates, explorer).
    """
    rows = []
    explorer: list[dict] = []
    for fx in fixtures.itertuples():
        for team, opponent in (
            (fx.home_team_raw, fx.away_team_raw),
            (fx.away_team_raw, fx.home_team_raw),
        ):
            label = f"{fx.home_team_raw} v {fx.away_team_raw}"
            for sel in squad(
                squads, resolution, team, 14, lineups.get(f"{team}|{label}"),
                history=history, as_of=as_of,
            ):
                by_market = {}
                for market, models in (("committed", committed), ("drawn", drawn)):
                    dists = {}
                    whys = {}
                    for cid, model in models.items():
                        dists[cid], whys[cid] = model.predict_one(
                            sel.lookup, opponent, as_of,
                            confirmed="start" if sel.confirmed else None,
                            team=team,
                        )
                    by_market[market] = (dists, whys)
                    market_key = (
                        "player_fouls_committed" if market == "committed" else "player_fouls_drawn"
                    )
                    for line in (0.5, 1.5, 2.5):
                        probs = {
                            cid: calibration.correct(d.prob_over(line), market_key, line)
                            for cid, d in dists.items()
                        }
                        if max(probs.values()) < 0.12 or min(probs.values()) > 0.97:
                            continue
                        rows.append(
                            {
                                "player": sel.display,
                                "fullName": sel.full,
                                "position": sel.position,
                                "hasHistory": sel.history is not None,
                                "team": team,
                                "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
                                "kickoff": fx.kickoff_utc.isoformat(),
                                "market": market,
                                "line": line,
                                "probs": probs,
                                "whys": whys,
                            }
                        )

                explorer.append(
                    _explorer_row(sel, team, opponent, fx, by_market)
                )
    return rows, explorer


def _explorer_row(sel, team: str, opponent: str, fx, by_market: dict) -> dict:
    """One player, every market, every line, every model, in one compact row.

    Held as arrays rather than nested objects because the site filters this on
    every keystroke and the file is downloaded once. Model order is fixed by the
    `models` key on the payload.
    """
    committed_d, committed_w = by_market["committed"]
    drawn_d, _ = by_market["drawn"]
    ids = list(committed_d)

    # Involvements: committed plus won, as one number. Convolved under
    # independence, which was measured to beat the correlation-corrected
    # version. See foulgorithm.models.involvement.
    involved = {cid: involvement.combine(committed_d[cid], drawn_d[cid]) for cid in ids}

    def grid(dists: dict, market_key: str | None) -> list[list[float]]:
        return [
            [
                round(
                    calibration.correct(dists[cid].prob_over(line), market_key, line)
                    if market_key
                    else dists[cid].prob_over(line),
                    4,
                )
                for cid in ids
            ]
            for line in EXPLORER_LINES
        ]

    # The house model's view, not whichever character happens to sort first.
    # Expected minutes differ per character because their memories differ.
    why = committed_w[HOUSE_MODEL]
    return {
        "player": sel.display,
        "fullName": sel.full,
        "position": sel.position,
        "team": team,
        "opponent": opponent,
        "fixture": f"{fx.home_team_raw} v {fx.away_team_raw}",
        "kickoff": fx.kickoff_utc.isoformat(),
        "minutes": round(why["expectedMinutes"], 1),
        "startProbability": why.get("startProbability"),
        "confirmed": bool(sel.confirmed),
        "thin": why["effectiveMatches"] < THIN_EVIDENCE or sel.history is None,
        "expected": {
            "committed": round(committed_d[HOUSE_MODEL].mean(), 2),
            "drawn": round(drawn_d[HOUSE_MODEL].mean(), 2),
            "involvements": round(involved[HOUSE_MODEL].mean(), 2),
        },
        # Involvements are not calibration-corrected: the correction was fitted
        # on the two component markets and does not transfer to their sum.
        "committed": grid(committed_d, "player_fouls_committed"),
        "drawn": grid(drawn_d, "player_fouls_drawn"),
        "involvements": grid(involved, None),
        # The full shape, house model only, so a row can be expanded into the
        # distribution behind its headline number. Truncated where the tail
        # stops mattering, which keeps the payload honest rather than long.
        "pmf": {
            "committed": _pmf(committed_d[HOUSE_MODEL]),
            "drawn": _pmf(drawn_d[HOUSE_MODEL]),
            "involvements": _pmf(involved[HOUSE_MODEL]),
        },
    }


def _pmf(dist, cutoff: float = 0.995, cap: int = 9) -> list[float]:
    """The distribution as a short list, cut where the remaining tail is noise."""
    out, run = [], 0.0
    for k in range(cap + 1):
        p = dist.pmf(k)
        out.append(round(p, 4))
        run += p
        if run >= cutoff:
            break
    return out


def _preference(cid: str, row: dict) -> float:
    """How much this character wants this bet. Higher is keener.

    Boldness is deviation from the pack, NOT low probability. A character
    backing a 70% shot the others price at 55% is being bold; one backing a
    45% shot everybody agrees on is just accepting a longer price.
    """
    own = row["probs"][cid]
    others = [p for c, p in row["probs"].items() if c != cid]
    pack = sum(others) / len(others)
    edge = own - pack
    why = row["whys"][cid]

    if cid == "tayler":
        # Terror wants agreement and evidence, and dislikes standing out.
        return own - abs(edge) * 2.0 + min(why["effectiveMatches"], 40) / 200
    if cid == "alan":
        # Anger backs whatever it has most recently seen, hardest.
        return edge * 3.0 + why["ratePer90"] * 0.2
    if cid == "bdog":
        # Bravery goes where the pack is not, and tolerates thin evidence.
        return edge * 4.0 - min(why["effectiveMatches"], 40) / 400
    if cid == "valentina":
        # Violence reads the matchup above all else.
        return (why["opponentFactor"] - 1.0) * 4.0 + edge * 1.5
    # Lust chases the biggest raw numbers and the biggest names.
    return why["ratePer90"] * 1.5 + edge


def _equal_risk_slip(cid: str, candidates: list[dict], target=(0.10, 0.20)) -> list[dict]:
    """Five picks whose combined probability lands in a fixed band.

    Every character therefore risks the same and stands to win the same, so
    comparing them is finally apples to apples. Temperament shows in WHICH five
    get there, not in picking easier bets. See docs/15-next-phase.md.
    """
    ranked = sorted(candidates, key=lambda r: -_preference(cid, r))

    chosen: list[dict] = []
    seen: set[str] = set()
    combined = 1.0

    for row in ranked:
        if len(chosen) == PICKS_PER_CHARACTER:
            break
        if row["player"] in seen:
            continue
        p = row["probs"][cid]
        remaining = PICKS_PER_CHARACTER - len(chosen) - 1
        after = combined * p
        # Keep the slip reachable: with `remaining` legs still to add, the best
        # and worst it could still end up must straddle the target band.
        if after * (0.97**remaining) > target[1]:
            continue
        if after * (0.30**remaining) < target[0] and remaining > 0:
            continue
        chosen.append(row)
        seen.add(row["player"])
        combined = after

    if len(chosen) < PICKS_PER_CHARACTER:
        for row in ranked:
            if len(chosen) == PICKS_PER_CHARACTER:
                break
            if row["player"] in seen:
                continue
            chosen.append(row)
            seen.add(row["player"])
        combined = 1.0
        for row in chosen:
            combined *= row["probs"][cid]

    # Repair pass: swap the least-wanted leg for one that moves the slip toward
    # the band, keeping the character's preference order otherwise intact.
    for _ in range(60):
        if target[0] <= combined <= target[1]:
            break
        need_higher = combined < target[0]
        worst = min(range(len(chosen)), key=lambda i: _preference(cid, chosen[i]))
        current = chosen[worst]
        best_swap = None
        for row in ranked:
            if row["player"] in seen and row["player"] != current["player"]:
                continue
            candidate = combined / current["probs"][cid] * row["probs"][cid]
            if need_higher and candidate <= combined:
                continue
            if not need_higher and candidate >= combined:
                continue
            distance = min(abs(candidate - target[0]), abs(candidate - target[1]))
            if target[0] <= candidate <= target[1]:
                distance = -1.0
            if best_swap is None or distance < best_swap[0]:
                best_swap = (distance, row, candidate)
        if best_swap is None:
            break
        _, row, combined = best_swap
        seen.discard(current["player"])
        seen.add(row["player"])
        chosen[worst] = row

    return chosen


def _slip_at_odds(cid: str, candidates: list[dict], target: float) -> dict | None:
    """Build this character's best slip landing near a target price.

    Legs are added in the character's own preference order until the combined
    probability reaches 1/target. The NUMBER of legs is free, which is what
    makes the tiers comparable: reaching 10.0 takes more legs or bolder ones,
    and each character gets there its own way.
    """
    wanted = 1.0 / target
    ranked = sorted(candidates, key=lambda r: -_preference(cid, r))

    chosen: list[dict] = []
    seen: set[str] = set()
    combined = 1.0

    for row in ranked:
        if len(chosen) >= MAX_LEGS_PER_TIER:
            break
        if row["player"] in seen:
            continue
        p = row["probs"][cid]
        after = combined * p
        # Stop before overshooting: a slip priced longer than asked for is not
        # the tier it claims to be.
        if after < wanted * 0.75 and chosen:
            continue
        chosen.append(row)
        seen.add(row["player"])
        combined = after
        if combined <= wanted:
            break

    if not chosen or combined > wanted * 1.6:
        return None

    fair = 1 / combined
    legs = len(chosen)
    est = odds_math.offered(fair, legs=legs)
    return {
        "target": target,
        "targetLabel": odds_math.fractional(target),
        # Decimal for the price we computed, fractional only for the round tier
        # it was built to. limit_denominator on an arbitrary price produces
        # things like 269/20, which is correct and unreadable.
        "actualOdds": round(fair, 2),
        "probability": round(combined, 4),
        "outOf100": round(combined * 100),
        # An estimate and never an observation. No player-fouls price has ever
        # been published anywhere we can reach, so this is a stated assumption
        # with the margin shown beside it on the page.
        #
        # No verdict is attached, deliberately. The estimate is derived from
        # the fair price by removing a margin, so any comparison between the
        # two is circular and would always read "below fair". What IS worth
        # saying is how much of the combination the margin eats, which is the
        # take-out, and it is the reason accumulators get pushed.
        "estimatedOffer": round(est, 2),
        "legCount": legs,
        "takeOut": round(odds_math.take_out(legs=legs), 3),
        "floor": round(odds_math.floor(fair), 2),
        "legs": [_leg(row, cid) for row in chosen],
    }


def _leg(row: dict, cid: str) -> dict:
    p = row["probs"][cid]
    others = [q for k, q in row["probs"].items() if k != cid]
    pack = sum(others) / len(others)
    why = row["whys"][cid]
    return {
        "player": row["player"],
        # Settlement joins on the full name. "Havertz" cannot be matched
        # against "Kai Havertz", and a half-matching join is worse than none.
        "fullName": row.get("fullName") or row["player"],
        "team": row["team"],
        "fixture": row["fixture"],
        "kickoff": row["kickoff"],
        "market": row["market"],
        "line": row["line"],
        "fouls": int(row["line"] + 0.5),
        "prob": round(p, 4),
        "outOf100": round(p * 100),
        "packProb": round(pack, 4),
        "edge": round(p - pack, 4),
        "band": band(p),
        "thin": why["effectiveMatches"] < THIN_EVIDENCE,
    }


def _character_picks(cid, candidates) -> dict:
    c = characters.get(cid)
    chosen = _equal_risk_slip(cid, candidates)

    picks = []
    combined = 1.0
    for row in chosen:
        p = row["probs"][cid]
        why = row["whys"][cid]
        others = [q for k, q in row["probs"].items() if k != cid]
        pack = sum(others) / len(others)
        combined *= p
        picks.append(
            {
                "player": row["player"],
                "team": row["team"],
                "fixture": row["fixture"],
                "kickoff": row["kickoff"],
                "market": row["market"],
                "line": row["line"],
                "prob": round(p, 4),
                "packProb": round(pack, 4),
                "edge": round(p - pack, 4),
                "band": band(p),
                "outOf100": round(p * 100),
                "fair": round(1 / p, 2),
                "floor": round((1 / p) * (1 + EDGE_MARGIN), 2),
                "why": why,
                "thin": why["effectiveMatches"] < THIN_EVIDENCE or not row.get("hasHistory", True),
                "position": row.get("position"),
            }
        )

    in_band = 0.10 <= combined <= 0.20
    return {
        "id": c.id,
        "name": c.name,
        "emotion": c.emotion,
        "tagline": c.tagline,
        "settings": pm.CHARACTER_SETTINGS[cid],
        "picks": picks,
        "combinedProb": round(combined, 4),
        "combinedFair": round(1 / combined, 1) if combined > 0 else None,
        "averageProb": round(sum(p["prob"] for p in picks) / len(picks), 3) if picks else 0,
        "averageEdge": round(sum(p["edge"] for p in picks) / len(picks), 4) if picks else 0,
        "inBand": in_band,
        "tiers": [
            t for t in (_slip_at_odds(cid, candidates, target) for target in ODDS_TIERS)
            if t
        ],
    }


def _formations(lineups: dict) -> dict:
    """The confirmed shape per club per fixture, so a pitch can be drawn.

    The league publishes the formation as LINES of player ids, goalkeeper first,
    which is the real shape rather than something inferred from position codes.
    A back three and a back four are indistinguishable from codes alone.
    """
    out: dict[str, dict] = {}
    for key, lu in lineups.items():
        if not lu.lines:
            continue
        out.setdefault(lu.fixture, {})[lu.team] = {
            "formation": lu.formation,
            "lines": [
                [
                    {
                        "player": spot.name,
                        "position": spot.position,
                        "detail": spot.detail,
                        "shirt": spot.shirt,
                        "captain": spot.captain,
                    }
                    for spot in line
                ]
                for line in lu.lines
            ],
            "bench": [
                {"player": b.name, "position": b.position, "detail": b.detail, "shirt": b.shirt}
                for b in lu.bench
            ],
        }
    return out


def _fixture_slips(candidates: list[dict], fixtures) -> dict:
    """Every character's ladder, built inside a single fixture.

    Built per fixture rather than across the round because that is the unit a
    reader is actually looking at. A slip mixing three different matches is not
    a read on a game, it is a read on a Saturday.
    """
    out: dict[str, dict] = {}
    for fx in fixtures.itertuples():
        label = f"{fx.home_team_raw} v {fx.away_team_raw}"
        here = [c for c in candidates if c["fixture"] == label]
        if not here:
            continue
        by_character = {}
        for cid in pm.CHARACTER_SETTINGS:
            tiers = [t for t in (_slip_at_odds(cid, here, target) for target in ODDS_TIERS) if t]
            if tiers:
                by_character[cid] = tiers
        if by_character:
            out[label] = by_character
    return out


if __name__ == "__main__":
    result = publish()
    t = result["trainedOn"]
    print(f"Trained on {t['playerMatches']:,} player-matches, {t['players']:,} players "
          f"({t['from']} to {t['to']})\n")
    print("TOP FOULERS THIS ROUND")
    print(f"  {'player':<24}{'fixture':<30}{'mins':>6}{'1+':>7}{'2+':>7}  band")
    for r in result["topFouler" "s"][:10]:
        c = r["committed"]
        print(f"  {r['player']:<24}{r['fixture']:<30}{r['expectedMinutes']:>6.0f}"
              f"{c['p1plus']:>7.0%}{c['p2plus']:>7.0%}  {c['band1']}")
    print("\nCHARACTER PICKS")
    for block in result["picks"]:
        flag = "" if block["inBand"] else "  [OUT OF BAND]"
        print(f"\n  {block['name']} ({block['emotion']}) — avg {block['averageProb']:.0%}, "
              f"combined {block['combinedFair']}/1, edge {block['averageEdge']:+.1%}{flag}")
        for t in block["tiers"]:
            legs = " + ".join(f"{l['player']} {l['fouls']}+" for l in t["legs"])
            print(f"    @{t['target']:>5.1f}  actual {t['actualOdds']:>6.2f}  "
                  f"{t['outOf100']:>3}/100  {legs[:74]}")
        for p in block["picks"]:
            verb = "commits" if p["market"] == "committed" else "draws"
            print(f"    {p['player']:<22} {int(p['line']+0.5)}+ {verb:<7} "
                  f"{p['prob']:>5.0%} (pack {p['packProb']:>4.0%}) floor {p['floor']}")
