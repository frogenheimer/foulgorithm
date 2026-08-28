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
from foulgorithm.models import ensemble
from foulgorithm.publish import league
from foulgorithm.characters import reasons as character_reasons
from foulgorithm.publish import combinations as combos
from foulgorithm.identity import players as identity
from foulgorithm.identity.teams import history_name, to_fpl
from foulgorithm.markets import odds as odds_math
from foulgorithm.models import calibration, involvement, player_models as pm
from foulgorithm.sources import football_data, fpl, league_stats
from foulgorithm.sources.lineups import for_round as confirmed_lineups
from foulgorithm.store import positions as positions_store
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


def name_key(name: str) -> tuple[str, ...]:
    """A player's identity, independent of the order his names arrive in.

    Wataru Endo reached Liverpool's bench twice, once as "Wataru Endo" from FPL
    and once as "Endo Wataru" from the team sheet. Ao Tanaka did the same at
    Leeds. Family name first in one source, given name first in the other, which
    docs/04-identity-resolution.md flags and the identity resolver already
    handles by comparing unordered tokens. Squad assembly deduped on the
    normalised string instead, so two orderings were two players.

    Sorted tokens, so both orderings land on one key. Used ONLY to decide
    whether a player is already in the list. It never picks which spelling is
    displayed and never confirms a match against history on its own.
    """
    return tuple(sorted(fpl.normalise(name).split()))


def find_squad_member(by_key: dict, name: str):
    """The squad member a team sheet is referring to, or None.

    Exact key first. Failing that, a subset match: every word of one name
    appearing in the other, which is how "Ben White" reaches FPL's "Benjamin
    White" and "Gabriel Magalhaes" reaches "Gabriel dos Santos Magalhaes".

    Two guards, both borrowed from the identity resolver, which has had this
    right all along:

      - At least two words must overlap, so a lone surname never resolves. This
        is the rule that stops Danny Ward the goalkeeper inheriting Danny Ward
        the striker's foul rate.
      - Exactly one candidate, or nothing. An ambiguous match is refused rather
        than guessed, per ADR-007.
    """
    key = name_key(name)
    if key in by_key:
        return by_key[key]

    tokens = set(key)
    if len(tokens) < 2:
        return None

    candidates = [
        member
        for other, member in by_key.items()
        if len(set(other) & tokens) >= 2 and (set(other) <= tokens or tokens <= set(other))
    ]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return None  # ambiguous, refuse rather than guess

    # Last resort: a surname unique within this ONE club's squad.
    #
    # Team sheets use the name the player goes by and FPL uses the formal one:
    # "Andy Robertson" against "Andrew Robertson", "Ben White" against
    # "Benjamin White". Those share only the surname, so the two-word rule above
    # refuses them, and twelve players reached the site with no position.
    #
    # The reason the two-word rule exists is Danny Ward the goalkeeper
    # inheriting Danny Ward the striker's rate. That is a collision between two
    # players with one surname, so requiring the surname to be unique among the
    # thirty-odd names at a single club addresses it directly. Across the league
    # this would be reckless; inside one squad it is the same check a person
    # reading the team sheet would make.
    surname = key[-1] if key else ""
    if not surname:
        return None
    shares = [member for other, member in by_key.items() if other and surname in other]
    return shares[0] if len(shares) == 1 else None


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
        # Keyed the same way the dedupe is, so a team sheet writing a name in
        # the other order still finds the squad member. Missing him here cost
        # the position, which reached the bench as a dash.
        by_key = {name_key(p.name): p for p in players}

        def selection_for(name: str, starting: bool) -> Selection:
            match = find_squad_member(by_key, name)
            return Selection(
                display=match.web_name if match else name.split()[-1],
                full=match.name if match else name,
                history=resolution.matched.get(match.name) if match else None,
                position=match.position if match else "?",
                available=True,
                news="",
                confirmed=starting,
            )

        # The named substitutes get predictions too. Without them the pitch can
        # only offer players already on it, so "swap someone out" had nothing to
        # swap in: a confirmed eleven is eleven, and every other name had no
        # numbers attached.
        # Both keys go into `seen`: the name the team sheet used AND the name it
        # resolved to. A subset match means those differ ("Ben White" resolving
        # to FPL's "Benjamin White"), and recording only the team sheet's meant
        # the squad loop below did not recognise him and added him a second time.
        out: list[Selection] = []
        seen: set[tuple[str, ...]] = set()

        def remember(sel: Selection, original: str) -> None:
            seen.add(name_key(original))
            seen.add(name_key(sel.full))
            out.append(sel)

        for n in lineup.starters:
            remember(selection_for(n, True), n)
        for name in lineup.substitutes:
            if name_key(name) not in seen:
                remember(selection_for(name, False), name)

        # Everyone else available. A named eleven and nine substitutes is the
        # match; the rest of the squad is who a reader might ask about.
        for p in players:
            if name_key(p.name) in seen or not p.available:
                continue
            out.append(
                Selection(
                    display=p.web_name,
                    full=p.name,
                    history=resolution.matched.get(p.name),
                    position=p.position,
                    available=True,
                    news=p.news,
                    confirmed=False,
                )
            )
            seen.add(name_key(p.name))
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

    # Then everyone else who could feature.
    #
    # Cutting at the limit meant a player with no starts this season never
    # appeared however obviously he belongs in a foul market: Rio Ngumoha wins
    # fouls for Liverpool and was invisible, along with 110 other available
    # players. The likely eleven still leads, so the pitch picks the same
    # starters. This only widens what can be SELECTED. Training is untouched and
    # always was: history covers everyone who ever played.
    chosen = {p.name for p in ranked}
    ranked = ranked + sorted(
        (
            p
            for p in players
            if p.name not in chosen and p.available and (p.chance is None or p.chance >= 50)
        ),
        key=lambda p: (-p.minutes, p.name),
    )

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


def _season_evidence(history: pd.DataFrame) -> pd.DataFrame | None:
    """Season-total evidence for the rate blend. The C1 change.

    Gated by `backtest/season_total_study.py`: with running totals attached,
    the blend recovered 78% of the stale-to-oracle log loss gap on committed
    and 87% on drawn, with calibration improving. The in-progress season is
    refreshed first so today's predictions read today's totals; a failed
    refresh degrades to the reading on disk, said out loud, because a stale
    reading beats no reading and silence beats neither.
    """
    from foulgorithm.features import season_totals
    from foulgorithm.sources import league_seasons
    from foulgorithm.store import player_seasons

    try:
        league_seasons.refresh_current()
    except Exception as exc:  # noqa: BLE001 - degrade loudly, never silently
        print(f"  current-season refresh failed, using the reading on disk: {exc}")

    try:
        api = player_seasons.load()
    except Exception as exc:  # noqa: BLE001 - reported; the blend is optional, lying is not
        print(f"  season totals unreadable, predicting without them: {exc}")
        return None

    api = api[api["season"].astype(str).str.match(r"\d{4}/\d{2}")]
    if api.empty:
        print("  no season totals on disk, predicting without them")
        return None

    evidence = season_totals.evidence(api, history)
    report = season_totals.last_report()
    print(
        f"  season evidence: {report['rows']:,} rows for {report['players']:,} "
        f"players, {report['anomalies']} anomalies, {report['unresolved']} unresolved"
    )
    return evidence


def _match_context():
    """Opponent factors from the match store. The C2 stage one change.

    Gated by `backtest/team_context_study.py`. On equal footing the swap is
    neutral, which is the point: it is the same quantity from a source that
    has not frozen. Under production conditions, a frozen rate against a
    live store, it wins on both markets, mostly on calibration: ECE 0.0137
    to 0.0105 on committed and 0.0108 to 0.0074 on drawn.

    Referees are deliberately NOT wired. Published player predictions carry
    no referee factor today, so that would be an addition rather than a
    swap, and the same study measured it adding nothing. This project has
    shipped three things that were real signal and a worse model.
    """
    from foulgorithm.features.team_context import MatchContextSource
    from foulgorithm.store.matches import load_matches

    try:
        matches = load_matches()
    except Exception as exc:  # noqa: BLE001 - degrade loudly to the archive path
        print(f"  match store unavailable, opponent factors stay on the archive: {exc}")
        return None
    if matches.empty:
        print("  match store empty, opponent factors stay on the archive")
        return None
    print(f"  opponent context from {len(matches):,} matches to {matches['kickoff_utc'].max():%b %Y}")
    return MatchContextSource(matches)


def publish(
    output: Path = OUTPUT,
    fixtures_override: list[dict] | None = None,
    record: bool = True,
    competition: str | None = None,
    lineups_override: dict | None = None,
    lineups_source: str | None = None,
) -> dict:
    """Predict a round and write the payload.

    `fixtures_override` feeds the engine a hand-picked slate instead of the
    league's next round, and `record=False` makes the run an EXHIBITION:
    the payload and fixture pages are written but nothing enters the
    append-only stores, so nothing is graded and nothing scores in the
    league. Both exist for cup ties (publish/cups.py); a league publish
    passes neither.
    """
    history = load_player_matches()

    if fixtures_override is not None:
        fixtures = pd.DataFrame(fixtures_override)
    else:
        # The league's list decides what is next; football-data supplies the
        # referee and the odds. Reading the round from football-data meant
        # predicting games already played, because that file holds one round
        # and does not roll over until midweek. See features/next_round.py.
        from foulgorithm.features import next_round

        fixtures = pd.DataFrame(next_round.fetch())
    as_of = datetime.now(timezone.utc)
    if fixtures.empty:
        print("  no upcoming fixtures, nothing to predict")

    if fixtures_override is not None:
        # A hand-fed slate never asks the league's feed: cup elevens come from
        # their own source (jobs/cup_watch.py) or nowhere. Asking the league
        # for a cup tie returns nothing while looking like 'not out yet'.
        lineups = lineups_override or {}
    else:
        try:
            lineups = confirmed_lineups()
        except Exception as exc:  # noqa: BLE001 - reported, never silently empty
            print(f"  confirmed lineups unavailable: {exc}")
            lineups = {}
    # Remember where the team sheets actually put people, then read the memory
    # back for the predicted pitches. See store/positions.py.
    positions_store.remember(lineups)
    seen_roles = positions_store.load()

    # Only the ones for fixtures we are actually predicting.
    #
    # The feed returns every confirmed eleven it holds, including last round's,
    # and the site reported that count against the number of fixtures on the
    # board. Once the board became the round that is COMING rather than the one
    # just played, it read "18 of 2".
    # Keyed "Club|Home v Away", not by club. Filtering on the club alone matched
    # nothing and produced a confident zero, which is the worse failure: it looks
    # exactly like "no lineups are out yet" and would have stayed zero at kickoff.
    if not fixtures.empty:
        lineups = scope_lineups(
            lineups,
            {f"{row.home_team_raw} v {row.away_team_raw}" for row in fixtures.itertuples()},
        )

    season_evidence = _season_evidence(history)

    squads = fpl.current_squads()
    everyone = [p for club in squads.values() for p in club]
    # The resolution universe includes evidence-only names, so a player the
    # archive has never seen but the league's totals have, a 2025/26 arrival
    # say, resolves to the name his evidence is filed under rather than to
    # nothing.
    names = pd.Index(history["player"].unique())
    if season_evidence is not None and len(season_evidence):
        names = names.union(pd.Index(season_evidence["player"].unique()))
    resolution = identity.resolve(everyone, names)

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
    context = _match_context()
    for model in list(committed.values()) + list(drawn.values()):
        model.fit(history)
        if season_evidence is not None and len(season_evidence):
            model.attach_season_evidence(season_evidence)
        if context is not None:
            model.use_match_context(context)

    house_c, house_d = committed[HOUSE_MODEL], drawn[HOUSE_MODEL]

    board = []
    predicted_shapes: dict[str, dict] = {}
    all_rows: list[dict] = []

    for fx in fixtures.itertuples():
        fixture_block = {
            "key": f"{fx.home_team_raw}-{fx.away_team_raw}",
            "home": fx.home_team_raw,
            "away": fx.away_team_raw,
            "kickoff": fx.kickoff_utc.isoformat(),
            # Absent on league rows; a hand-fed cup row names its competition
            # and the fixture page shows it. See publish/cups.py.
            "competition": getattr(fx, "competition", None),
            # NaN, not None, is what a missing referee becomes once the rows go
            # through pandas, and NaN is not JSON. It reached the site as a
            # literal `NaN` token and broke the build. A fixture with no
            # appointment yet is a real and common state, so it has to survive.
            "referee": _or_none(fx.referee_raw),
            "lineupConfirmed": any(
                f"{t}|{fx.home_team_raw} v {fx.away_team_raw}" in lineups
                for t in (fx.home_team_raw, fx.away_team_raw)
            ),
            "teams": {},
        }
        for team, opponent in ((fx.home_team_raw, fx.away_team_raw), (fx.away_team_raw, fx.home_team_raw)):
            players = []
            label = f"{fx.home_team_raw} v {fx.away_team_raw}"
            selections = []
            for sel in squad(
                squads, resolution, team,
                lineup=lineups.get(f"{team}|{label}"),
                history=history, as_of=as_of,
            ):
                # A confirmed starter is a certainty, not a probability. Say so,
                # and the minutes mixture drops its unused branch entirely.
                selections.append(sel)
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
            if not any(sel.confirmed for sel in selections):
                shape = _predicted_shape(selections, roles=seen_roles)
                if shape:
                    predicted_shapes.setdefault(label, {})[team] = shape

            fixture_block["teams"][team] = sorted(
                players, key=lambda r: -r["committed"]["p1plus"]
            )
        fixture_block["compare"] = _compare(history, fixture_block, as_of)
        fixture_block["summary"] = _summary(fixture_block)
        fixture_block["houseSheet"] = _house_sheet(fixture_block)
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

    # Identical shapes for every character, so the table measures judgement
    # rather than difficulty. See publish/league.py. Standings come first
    # because Justine's selection covets the current leader's numbers.
    character_ids = list(pm.CHARACTER_SETTINGS)
    standings = _standings(character_ids)
    leader = standings[0]["id"] if standings and standings[0]["played"] > 0 else None
    slates = league.build_slates(candidates, character_ids, context={"leader": leader})

    top = sorted(all_rows, key=lambda r: -r["committed"]["p1plus"])[:12]

    fixture_slips = _fixture_slips(candidates, fixtures)
    best_picks = {
        label: pick
        for label, by_character in fixture_slips.items()
        if (pick := _best_pick(by_character))
    }
    # The card, the matrix and the league table now trace to the same picks:
    # the committed slates, not the display ladders. See _fixture_options.
    fixture_options = _fixture_options(slates, candidates)
    confirmed_fixtures = {key.split("|", 1)[-1] for key in lineups}
    for label, options in fixture_options.items():
        for option in options:
            option["lineupsConfirmed"] = label in confirmed_fixtures

    # Keep what each card says, so it can be marked right or wrong afterwards.
    if record:
        _record_cards(fixture_options, fixtures, as_of)

    payload = {
        "generatedAt": as_of.replace(microsecond=0).isoformat(),
        "competition": competition,
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
            # None means that line is published raw: the refit measured the
            # correction there costing held-out accuracy, and a correction
            # measured to hurt does not ship. See the modelling log,
            # 2026-08-24, and backtest/calibration_fit.py.
            "committed": {
                str(line): calibration.factor("player_fouls_committed", line)
                for line in (0.5, 1.5, 2.5)
            },
            "drawn": {
                str(line): calibration.factor("player_fouls_drawn", line)
                for line in (0.5, 1.5, 2.5)
            },
            "note": "Probabilities are corrected only where a correction "
                    "measurably helps held-out predictions. A missing factor "
                    "means that line is published as the model says it.",
        },
        "squads": {
            "source": "Fantasy Premier League API",
            "players": len(everyone),
            "resolved": len(resolution.matched),
            "unresolved": len(resolution.unmatched),
        },
        "lineups": {
            "source": lineups_source or "Premier League API",
            "confirmed": len(lineups),
            "note": "Confirmed elevens appear about an hour before kickoff. "
                    "Until then these are predicted from current squads.",
        },
        "topFoulers": top,
        # What we say each of these fixtures will produce, kept permanently so a
        # played card can still show it. See store/expected_totals.py.
        "expectedTotals": _keep_expected_totals(board, as_of),
        "board": board,
        "picks": picks,
        "fixtureSlips": fixture_slips,
        "bestPicks": best_picks,
        "fixtureOptions": fixture_options,
        # What past cards said, marked against what happened. See
        # store/published_picks.py for why it is the last version before kickoff.
        "settledCards": _settled_cards(),
        "slates": {
            "shapes": _shapes_for(board),
            "byGame": slates,
            "confirmedFixtures": sorted(confirmed_fixtures),
            "note": "Identical shapes for all five on every game, so the table "
                    "measures which players they pick rather than how hard a "
                    "bet they chose.",
        },
        "standings": standings,
        # Confirmed shapes win; a predicted one fills a fixture the league has
        # not published an eleven for yet.
        "formations": {**predicted_shapes, **_formations(lineups)},
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

    # Each fixture's page data, separately, so the page outlives the round.
    # See publish/archive.py.
    from foulgorithm.publish import archive

    archive.write_round(payload)

    # Persist the claims themselves, separately from the page they render on.
    # The JSON above is a view and gets overwritten every run; this is the
    # record, and it is append-only.
    if record:
        payload["recorded"] = _record(board, picks, as_of, slates)
    else:
        payload["recorded"] = {
            "written": 0,
            "skipped": 0,
            "note": "exhibition: nothing enters the record",
        }
    return payload


def _shapes_for(board: list[dict]) -> list[dict]:
    """The bets' shapes for this board: bands from docs/42's date, shapes before."""
    if board and all(ensemble.priced(f["kickoff"]) for f in board):
        return [
            {"key": b.key, "label": b.label, "target": b.target, "low": b.low, "high": b.high}
            for b in ensemble.BANDS
        ]
    return [{"key": sl.key, "label": sl.label, "legs": sl.legs} for sl in ensemble.SLATES]


def _commit_slates(slates: dict, published: str) -> dict:
    """Record what each character committed to, as claim keys.

    Stored beside the claims rather than inside them. A slate leg is the same
    claim a tier already recorded, so writing it as a claim collides on the key,
    and the ledger is append-only so it cannot be added to one later. See
    store/slates.py.
    """
    from foulgorithm.store import slates as slate_store

    # The round's earliest kickoff, from the legs themselves. A slate may be
    # re-committed with confirmed lineups only before this moment; the binding
    # rule in publish/league.py reads it.
    kickoffs = [
        leg["kickoff"]
        for by_character in (slates or {}).values()
        for by_slate in (by_character or {}).values()
        for built in (by_slate or {}).values()
        if built and built.get("legs")
        for leg in built["legs"]
    ]
    first_kickoff = min(kickoffs) if kickoffs else None

    # Each game's gameweek, from the season export: the round's true
    # identity, stable however many times a gameweek is republished.
    matchweeks: dict[str, int] = {}
    season_path = Path("site/public/data/season.json")
    if season_path.exists():
        try:
            for fx in json.loads(season_path.read_text()).get("fixtures", []):
                if fx.get("matchweek"):
                    matchweeks[f"{fx.get('home')} v {fx.get('away')}"] = int(fx["matchweek"])
        except (OSError, json.JSONDecodeError, ValueError):
            matchweeks = {}

    committed = []
    for label, by_character in (slates or {}).items():
        for cid, by_slate in (by_character or {}).items():
            for slate_key, built in (by_slate or {}).items():
                if not built or not built["legs"]:
                    continue
                keys = []
                for leg in built["legs"]:
                    keys.append(
                        pred_store.Prediction(
                            published_at=published,
                            kickoff=leg["kickoff"],
                            fixture=leg["fixture"],
                            entity=leg.get("fullName") or leg["player"],
                            market=(
                                "player_fouls_committed"
                                if leg["market"] == "committed"
                                else "player_fouls_drawn"
                            ),
                            line=leg["line"],
                            probability=leg["prob"],
                            model_id=cid,
                            model_version="1.0.0",
                            lineup_confirmed=False,
                            thin=bool(leg.get("thin")),
                        ).key
                    )
                committed.append(
                    slate_store.Committed(
                        published_at=published,
                        round=slate_store.round_of(
                            first_kickoff or built["legs"][0]["kickoff"]
                        ),
                        character=cid,
                        slate=slate_key,
                        claim_keys=keys,
                        first_kickoff=first_kickoff,
                        fixture=label,
                        kickoff=built["legs"][0]["kickoff"],
                        matchweek=matchweeks.get(label),
                    )
                )
    return slate_store.append(committed)


def _settled_cards() -> dict:
    """Past fixture cards, with each leg marked landed, missed or undecided.

    Only fixtures we published a card for before kickoff appear. Cards shown
    before the store existed are absent and stay absent, because reconstructing
    what a card would have said is not the same as recording what it did say.
    """
    from foulgorithm.review import grade as grading
    from foulgorithm.store import predictions as pred_store
    from foulgorithm.store import published_picks

    try:
        graded = grading.load_all()
    except Exception:
        return {}

    claims = {row["key"]: row for row in pred_store.load_all()}
    outcomes: dict[tuple, bool] = {}
    for row in graded:
        claim = claims.get(row.get("key"))
        if not claim:
            continue
        market = "committed" if claim["market"].endswith("committed") else "drawn"
        outcomes[(claim["entity"], market, claim["line"])] = bool(row.get("won"))

        # Cards name players the short way; the ledger stores the full name.
        short = claim["entity"].split()[-1]
        outcomes.setdefault((short, market, claim["line"]), bool(row.get("won")))

    out = {}
    for fixture in published_picks.load_all():
        version = published_picks.final(fixture)
        if not version:
            continue
        scored = [published_picks.score(o, outcomes) for o in version["options"]]
        if any(o["landed"] is not None for o in scored):
            out[fixture] = {"version": version["version"], "options": scored}
    return out


def _record_cards(fixture_options: dict, fixtures, as_of) -> None:
    """Version what each fixture card is showing right now.

    A midweek model change should produce different picks, so this versions
    rather than freezes. The last version before kickoff is what gets scored,
    because that is what was on the card when the game started.
    """
    from foulgorithm.store import published_picks

    kickoffs = {
        f"{row.home_team_raw} v {row.away_team_raw}": row.kickoff_utc.isoformat()
        for row in fixtures.itertuples()
    }
    stamp = as_of.replace(microsecond=0).isoformat()
    for label, options in fixture_options.items():
        kickoff = kickoffs.get(label)
        if kickoff:
            published_picks.record(label, kickoff, options, stamp)


def _keep_expected_totals(board: list[dict], as_of) -> dict:
    """Record this round's expected totals, and return everything ever recorded.

    Eleven a side, not twenty-two off a combined list: a confirmed fixture
    carries exactly eleven a side and an unconfirmed one carries more, so
    slicing a flattened list took the wrong number from each side and made every
    unconfirmed fixture look quiet.
    """
    from foulgorithm.store import expected_totals

    totals = {}
    for fixture in board:
        label = f"{fixture['home']} v {fixture['away']}"
        # A cup tie shares the league fixture's label, and this store keys by
        # label. Unqualified, the cup's claim files under the league game's
        # identity, which reads as a post-hoc claim on a played match: the
        # exact thing this store exists to make impossible.
        if fixture.get("competition"):
            label = f"{label} ({fixture['competition']})"
        totals[label] = sum(
            sum((p.get("committed", {}).get("why", {}).get("expected_fouls") or 0)
                for p in squad[:11])
            for squad in fixture["teams"].values()
        )

    expected_totals.record(totals, as_of.replace(microsecond=0).isoformat())
    return expected_totals.load()


def scope_lineups(lineups: dict, playing: set[str]) -> dict:
    """Only the confirmed elevens for fixtures we are predicting.

    Keys are "Club|Home v Away", so the fixture is the part after the bar.
    Filtering on the club alone matched nothing and produced a confident zero.
    """
    if not playing:
        return lineups
    return {key: xi for key, xi in lineups.items() if key.split("|", 1)[-1] in playing}


def _or_none(value):
    """Anything pandas made missing, back to a JSON null."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _standings(character_ids: list[str]) -> list[dict]:
    """The table so far. Empty until slates start settling, and says so."""
    from foulgorithm.review import grade as grading
    from foulgorithm.store import predictions as pred_store

    try:
        graded = grading.load_all()
    except Exception:
        return league.table([], character_ids)
    from foulgorithm.store import slates as slate_store

    # Completed games, for the void backstop: a leg with no outcome once its
    # game is over voids rather than blocking the bet forever.
    completed: set[str] = set()
    season_path = Path("site/public/data/season.json")
    if season_path.exists():
        try:
            season = json.loads(season_path.read_text())
            completed = {
                f"{f.get('home')} v {f.get('away')}"
                for f in season.get("fixtures", [])
                if f.get("status") == "C"
            }
        except (OSError, json.JSONDecodeError):
            completed = set()

    committed = slate_store.load_all()
    joined = league.join_slates(graded, committed, completed=completed)
    rows = league.table(joined, character_ids)

    # Boldness: rarity by the house's own price, as columns and as the
    # tie-breaker behind foul difference. See league.boldness.
    bold = league.boldness(committed, graded, pred_store.load_all(), character_ids)
    for row in rows:
        row.update(bold.get(row["id"], {"boldness": 0.0, "winBoldness": 0.0}))
    rows.sort(
        key=lambda r: (
            -r["points"],
            -r["difference"],
            -r.get("winBoldness", 0.0),
            -r["legsLanded"],
            r["id"],
        )
    )
    return rows


def _record(board: list[dict], picks: list[dict], as_of, slates: dict | None = None) -> dict:
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
    #
    # One row per claim, not per tier. A character often carries the same player
    # and line across several tiers, and that is one opinion packaged more than
    # once, not several opinions. The tiers it appeared on are kept so a slip can
    # still be graded as a slip.
    slips: dict[tuple, dict] = {}
    for block in picks:
        for tier in block.get("tiers", []):
            for leg in tier["legs"]:
                market = (
                    "player_fouls_committed"
                    if leg["market"] == "committed"
                    else "player_fouls_drawn"
                )
                entity = leg.get("fullName") or leg["player"]
                claim = (leg["fixture"], entity, market, leg["line"], block["id"])
                held = slips.setdefault(
                    claim,
                    {
                        "kickoff": leg.get("kickoff") or as_of.isoformat(),
                        "prob": leg["prob"],
                        "thin": bool(leg.get("thin")),
                        "tiers": [],
                    },
                )
                if tier["target"] not in held["tiers"]:
                    held["tiers"].append(tier["target"])

    for (fixture, entity, market, line, model_id), held in slips.items():
        rows.append(
            pred_store.Prediction(
                published_at=published,
                kickoff=held["kickoff"],
                fixture=fixture,
                entity=entity,
                market=market,
                line=line,
                probability=held["prob"],
                model_id=model_id,
                model_version="1.0.0",
                lineup_confirmed=False,
                thin=held["thin"],
                extra={"tiers": held["tiers"]},
            )
        )

    for by_character in (slates or {}).values():
        for cid, by_slate in (by_character or {}).items():
            for built in (by_slate or {}).values():
                if not built:
                    continue
                for leg in built["legs"]:
                    rows.append(
                        pred_store.Prediction(
                            published_at=published,
                            kickoff=leg["kickoff"],
                            fixture=leg["fixture"],
                            entity=leg.get("fullName") or leg["player"],
                            market=(
                                "player_fouls_committed"
                                if leg["market"] == "committed"
                                else "player_fouls_drawn"
                            ),
                            line=leg["line"],
                            probability=leg["prob"],
                            model_id=cid,
                            model_version="1.0.0",
                            lineup_confirmed=False,
                            thin=bool(leg.get("thin")),
                            extra={},
                        )
                    )

    written = pred_store.append(rows)
    written["slates"] = _commit_slates(slates, published)
    return written


def _league_leaders() -> dict:
    """Current-season leaders. Context, not product, so a failure is survivable."""
    try:
        return league_stats.all_leaders(8)
    except Exception as exc:  # noqa: BLE001 - reported, never silently empty
        print(f"  league leaders unavailable: {exc}")
        return {}


#: The house sheet shows this many players per line group.
HOUSE_SHEET_PICKS = 3
#: The three tiers of the house sheet, badged in this order (docs/41).
HOUSE_SHEET_TIERS = ((1, "safe"), (2, "optimistic"), (3, "rogue"))
#: A 3+ group appears only when its best price clears this. Below it the
#: group is a list of longshots pretending to be shouts.
HOUSE_SHEET_3PLUS_FLOOR = 0.20


def _house_sheet(fixture: dict) -> dict:
    """The house model's flat shouts for one fixture, no character attached.

    Grouped by market and line, top three by the house's own price from the
    likely eleven a side. Stars mark the sheet's best, and a player stars at
    most ONCE, at his rarest worthwhile line: starring the same player at
    1+ and 2+ is one opinion dressed as two, and the two could never sit in
    the same bet anyway (Oliver, 2026-08-25). Fouls committed takes star
    precedence over fouls won at the same line, being the headline market.
    """
    eleven = [p for squad in fixture["teams"].values() for p in squad[:11]]

    groups = []
    for market in ("committed", "drawn"):
        for line in (1, 2, 3):
            ranked = sorted(
                eleven, key=lambda p: p[market].get(f"p{line}plus") or 0.0, reverse=True
            )[:HOUSE_SHEET_PICKS]
            picks = [
                {
                    "player": p["player"],
                    "fullName": p.get("fullName") or p["player"],
                    "outOf100": round((p[market].get(f"p{line}plus") or 0.0) * 100),
                    "star": False,
                    "tier": None,
                }
                for p in ranked
                if (p[market].get(f"p{line}plus") or 0.0) > 0
            ]
            if line == 3 and (
                not picks or picks[0]["outOf100"] < HOUSE_SHEET_3PLUS_FLOOR * 100
            ):
                continue
            if picks:
                groups.append({"market": market, "line": line, "picks": picks})

    # Three tiers, one per line, badged safest first: the 1+ shouts are the
    # SAFE tier, 2+ OPTIMISTIC, 3+ ROGUE. Rarest-first badging (28 August
    # 2026) put the sheet's headline on the longest shots; a reader wants
    # the safe call anchored by the best name and the rogue call falling to
    # the next. A player carries at most ONE tier on the whole sheet.
    badged: set[str] = set()
    for tier_line, tier in HOUSE_SHEET_TIERS:
        for group in groups:
            if group["line"] != tier_line:
                continue
            for pick in group["picks"]:
                if pick["player"] not in badged:
                    pick["tier"] = tier
                    pick["star"] = True
                    badged.add(pick["player"])
                    break

    return {"groups": groups}


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
                    _explorer_row(
                        sel, team, opponent, fx, by_market,
                        career=_career_rates(
                            {"committed": committed, "drawn": drawn}, sel, as_of
                        ),
                    )
                )
    return rows, explorer


def _career_rates(models: dict, sel, as_of) -> dict | None:
    """His plain per-90 in everything we hold, or None if he has never played.

    The house model supplies it, because any of them would give the same answer:
    this deliberately has no shrinkage and no decay, so no character setting
    touches it.
    """
    if sel.history is None:
        return None
    committed, nineties = models["committed"][HOUSE_MODEL].plain_rate(sel.history, as_of)
    drawn, _ = models["drawn"][HOUSE_MODEL].plain_rate(sel.history, as_of)
    if committed is None and drawn is None:
        return None
    return {
        "committed": round(committed, 2) if committed is not None else None,
        "drawn": round(drawn, 2) if drawn is not None else None,
        "involvements": (
            round(committed + drawn, 2)
            if committed is not None and drawn is not None
            else None
        ),
        "nineties": round(nineties, 1),
    }


def _explorer_row(sel, team: str, opponent: str, fx, by_market: dict, career=None) -> dict:
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
        # What the model expects in THIS match: his shrunk, time-decayed rate,
        # times his expected minutes, times the opponent and the referee, read
        # off the fitted distribution. Not an average of anything.
        "expected": {
            "committed": round(committed_d[HOUSE_MODEL].mean(), 2),
            "drawn": round(drawn_d[HOUSE_MODEL].mean(), 2),
            "involvements": round(involved[HOUSE_MODEL].mean(), 2),
        },
        # And the plain one, for comparison: fouls divided by nineties, over
        # everything we hold, unshrunk and undecayed. Where the two disagree the
        # difference IS the model's opinion, and a reader should see its size.
        "career": career,
        # Where the number mostly comes from. "promoted-club" means we have
        # never seen this player in this division and are leaning on how his
        # club fouled in the one below, which is an estimate and has to be
        # shown as one rather than sat next to a real record looking identical.
        "priorFrom": committed_w[HOUSE_MODEL].get("priorFrom"),
        "clubFactor": committed_w[HOUSE_MODEL].get("clubFactor"),
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


# The selection bounds (docs/38, unified 2026-08-25). Every competitor bets
# logic-first: preference is their own probability plus a temperament term
# clamped to THEIR sway. The sway widths ARE the personality now: Tayler's
# band is tight, B-Dog's is the widest, and nobody can veto arithmetic. The
# margin is what counts as a hot take: a leg where the character beats the
# pack's view by this much.
CHARACTER_SWAY: dict[str, float] = {
    "alan": 0.08,
    "lily": 0.07,
    "valentina": 0.08,
    "tayler": 0.03,
    "bdog": 0.12,
    "pax": 0.05,
    "justine": 0.08,
    "mabel": 0.10,
    "dottie": 0.10,
    "dele": 0.08,
    "ian": 0.02,
}
HOT_TAKE_MARGIN = 0.06


def _temperament(cid: str, row: dict, edge: float, pack: float, context: dict | None) -> float:
    """Each personality, expressed inside its band only. Same ingredients the
    old rogue formulas used, rescaled into probability units so the clamp
    means something."""
    own = row["probs"][cid]
    why = row["whys"][cid]
    evidence = min(why["effectiveMatches"], 40) / 40

    if cid == "alan":
        # Anger backs whatever it has most recently seen, hardest.
        return edge * 1.5 + min(why["ratePer90"], 3.0) * 0.02
    if cid == "lily":
        # Lust chases the biggest raw numbers and the biggest names.
        return min(why["ratePer90"], 3.0) * 0.04 + edge * 0.3
    if cid == "valentina":
        # Violence reads the matchup above all else.
        return (why["opponentFactor"] - 1.0) * 0.6 + edge * 0.4
    if cid == "tayler":
        # Terror wants agreement and evidence, and dislikes standing out.
        return evidence * 0.03 - abs(edge) * 0.6
    if cid == "bdog":
        # Bravery amplifies his own disagreements and tolerates thin evidence.
        return edge * 1.5 - evidence * 0.02
    if cid == "pax":
        # Persistence trusts the accumulated record and dislikes drama.
        return evidence * 0.05 - abs(edge) * 0.3
    if cid == "justine":
        # Jealousy covets the leader's number; the consensus when there is
        # no leader yet, which is the same instinct pointed at the crowd.
        leader = (context or {}).get("leader")
        target = row["probs"].get(leader) if leader else None
        return ((target if target is not None else pack) - own) * 0.8
    if cid == "mabel":
        # Madness wants the thin samples and the disagreements, any direction.
        return (1 - evidence) * 0.05 + abs(edge) * 0.6
    if cid == "dottie":
        # Deviance amplifies her genuine disagreements, and only those.
        return edge * 0.9
    if cid == "dele":
        # Delinquency backs the raw rate: the players referees know by name.
        return min(why["ratePer90"], 3.0) * 0.03
    # magicIan: the algorithm IS the personality. Near-pure belief.
    return 0.0


def _preference(cid: str, row: dict, context: dict | None = None) -> float:
    """How much this character wants this bet. Higher is keener.

    Logic first for everyone (docs/38, unified 2026-08-25): the character's
    own probability, plus a temperament clamped to their sway. An obvious
    pick cannot be vetoed by a personality; the close calls are where the
    eleven stop looking like each other. The old pure-temperament formulas
    made the five rogue: refusing your own best numbers under win/draw/loss
    scoring was points thrown away, and B-Dog was structurally punished for
    his own convictions.
    """
    own = row["probs"][cid]
    others = [p for c, p in row["probs"].items() if c != cid]
    pack = sum(others) / len(others) if others else own
    edge = own - pack

    sway = CHARACTER_SWAY.get(cid, 0.08)
    lean = _temperament(cid, row, edge, pack, context)
    return own + max(-sway, min(sway, lean))


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
        "reason": character_reasons.reason(
            cid,
            {
                "player": row["player"], "market": row["market"], "line": row["line"],
                "fouls": int(row["line"] + 0.5), "prob": p, "packProb": pack,
                "edge": p - pack, "thin": why["effectiveMatches"] < THIN_EVIDENCE,
            },
            why,
        ),
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
                "reason": character_reasons.reason(
                    cid,
                    {
                        "player": row["player"], "market": row["market"], "line": row["line"],
                        "fouls": int(row["line"] + 0.5), "prob": p, "packProb": pack,
                        "edge": p - pack,
                        "thin": why["effectiveMatches"] < THIN_EVIDENCE
                        or not row.get("hasHistory", True),
                    },
                    why,
                ),
            }
        )

    in_band = 0.10 <= combined <= 0.20
    return {
        "id": c.id,
        "name": c.name,
        "generation": c.generation,
        "emotion": c.emotion,
        "tagline": c.tagline,
        "settings": pm.CHARACTER_SETTINGS[cid],
        "summary": character_reasons.summary(cid, picks),
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


# A predicted back line never exceeds this. FPL codes wing-backs and pushed-up
# full-backs as defenders, and a back seven drawn from those codes is a shape
# no team has ever played.
MAX_PREDICTED_DEFENDERS = 5


def _predicted_shape(selections: list, roles: dict | None = None) -> dict | None:
    """A pitch for a fixture whose eleven has not been confirmed.

    Grouped from the predicted eleven's own positions rather than from a
    formation the league has not published: one goalkeeper, then defenders,
    midfielders and forwards, and the label falls out of the counts.

    ⚠️ This is a grouping, NOT a formation, and it is labelled as one. FPL codes
    a wing-back as a defender, so a side that plays three at the back with two
    wing-backs comes out as five defenders and a genuine 4-2-3-1 can come out as
    "6-4". Printing that as a formation would be inventing a shape the league
    has not published. The eleven itself is right about 78% of the time; the
    arrangement is only ever "these are the defenders".

    The defensive line is capped at MAX_PREDICTED_DEFENDERS: overflow moves
    into midfield, preferring whoever the league's team sheets last showed
    actually playing there (see store/positions.py), then the wide players,
    and a known centre-back only when nobody else is left. A promoted player
    keeps his D badge, because he is still a defender, just not in a back
    seven.
    """
    from foulgorithm.store import positions

    def code_for(sel) -> str:
        # FPL codes GKP/DEF/MID/FWD; anything unrecognised sits in midfield,
        # which is where an unknown is least wrong.
        code = (sel.position or "").strip().upper()[:1]
        return code if code in ("G", "D", "M", "F") else "M"

    # Exactly one goalkeeper, then ten outfielders in order. Grouping the first
    # eleven selections by position put every backup keeper on the pitch: a club
    # carries three and they all rank as goalkeepers, so the shape came out as
    # 5-2-1 with three men in goal.
    keepers = [sel for sel in selections if code_for(sel) == "G"]
    outfield = [sel for sel in selections if code_for(sel) != "G"]
    if not keepers or len(outfield) < 10:
        return None

    lines: dict[str, list] = {"G": keepers[:1], "D": [], "M": [], "F": []}
    for sel in outfield[:10]:
        lines[code_for(sel)].append(sel)

    def promotion_rank(sel) -> int:
        # Lower moves up sooner. 0 = the league last saw him in midfield,
        # 1 = last seen wide, 2 = never seen, 3 = a known centre-back.
        role = positions.role_for(roles or {}, getattr(sel, "full", None) or sel.display)
        role = role.lower()
        if "midfield" in role:
            return 0
        if "wing" in role or "full back" in role or "fullback" in role:
            return 1
        return 3 if role else 2

    overflow = len(lines["D"]) - MAX_PREDICTED_DEFENDERS
    if overflow > 0:
        ranked = sorted(
            enumerate(lines["D"]), key=lambda pair: (promotion_rank(pair[1]), -pair[0])
        )
        moving = {index for index, _ in ranked[:overflow]}
        lines["M"].extend(sel for i, sel in enumerate(lines["D"]) if i in moving)
        lines["D"] = [sel for i, sel in enumerate(lines["D"]) if i not in moving]

    order = ["G", "D", "M", "F"]
    out = [
        [
            {
                "player": sel.display,
                # The sel's own code, not the line it sits in: a defender
                # promoted into the midfield row keeps his D badge.
                "position": code_for(sel) if code != "G" else "G",
                "detail": sel.position or "",
                "shirt": None,
                "captain": False,
            }
            for sel in lines[code]
        ]
        for code in order
        if lines[code]
    ]
    # No formation label. See the docstring: a position grouping is not a shape,
    # and printing "6-4" as though it were one is a claim we cannot support.
    return {"formation": None, "lines": out, "bench": [], "predicted": True}


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
            "predicted": False,
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


# Six, not five. A five-foul ticket is usually four legs at 1+ plus one at 2+,
# which is close enough to "several players will foul someone" to not be a call
# at all. Six forces either a genuine 2+ opinion or a sixth player worth naming.
MIN_TOTAL_FOULS = 6

# A headline pick has to be worth reading. Ranking purely on distance from the
# pack found a 22/1 combination at four in a hundred, which is a lottery ticket
# wearing a recommendation. Ten in a hundred is still a long price and is
# something that actually happens.
MIN_PICK_PROBABILITY = 0.10


def _fixture_options(slates: dict, candidates: list[dict], limit: int = 5) -> dict[str, list[dict]]:
    """The crossover call per fixture: the legs the five most agree on, as one card.

    Derived from the COMMITTED slates, Oliver's call 2026-08-24, evening: the
    card, the matrix and the league table trace to the same picks, the ones
    that score, so backing here means a character actually committed to the
    leg rather than holding it somewhere in a display ladder. A leg counts a
    backer once per character however many of his three shapes repeat it,
    legs rank by how many of the five back them and then by the house number,
    and the card never represents a specific model: the probability shown per
    leg is the house blend, the unweighted mean of every character's number
    for that leg from the candidate table.
    """
    character_ids = {
        cid for by_character in (slates or {}).values() for cid in (by_character or {})
    }
    count = max(len(character_ids), 1)

    house_by_leg = {
        (r["fullName"], r["market"], r["line"]): sum(r["probs"].values()) / len(r["probs"])
        for r in candidates
        if r.get("probs")
    }

    by_fixture: dict[str, dict[tuple, dict]] = {}
    for label, by_character in (slates or {}).items():
        legs = by_fixture.setdefault(label, {})
        for cid, built_shapes in (by_character or {}).items():
            seen: set[tuple] = set()
            for built in (built_shapes or {}).values():
                for l in (built or {}).get("legs") or []:
                    key = (l["fullName"], l["market"], l["fouls"])
                    if key in seen:
                        continue
                    seen.add(key)
                    held = legs.get(key)
                    if held is None:
                        # Slate legs come from the candidate table in the same
                        # publish, so the blend is always there; the fallback to
                        # the character's own number only guards a stale caller.
                        house = house_by_leg.get(
                            (l["fullName"], l["market"], l["line"]), l["prob"]
                        )
                        legs[key] = {
                            "player": l["player"],
                            "fouls": l["fouls"],
                            "market": l["market"],
                            "_house": house,
                            "backers": 1,
                        }
                    else:
                        held["backers"] += 1

    out: dict[str, list[dict]] = {}
    for label, legs in by_fixture.items():
        if not legs:
            continue  # every shape passed on this game: no card, not a blank one
        ranked = sorted(legs.values(), key=lambda l: (-l["backers"], -l["_house"]))[:limit]
        combined = 1.0
        for l in ranked:
            combined *= l["_house"]
        out[label] = [
            {
                "band": "Consensus",
                "character": "consensus",
                "characterName": "The five",
                "tier": "",
                "odds": round(1.0 / combined, 2) if combined > 0 else 0.0,
                "outOf100": round(combined * 100),
                "houseOutOf100": round(combined * 100),
                "totalFouls": sum(l["fouls"] for l in ranked),
                "gap": 0.0,
                "backers": count,
                "legs": [
                    {
                        "player": l["player"],
                        "fouls": l["fouls"],
                        "market": l["market"],
                        "outOf100": round(l["_house"] * 100),
                        "backers": l["backers"],
                    }
                    for l in ranked
                ],
            }
        ]
    return out


def _best_pick(by_character: dict) -> dict | None:
    """One call per fixture, from whichever character makes the boldest case.

    Constrained to combinations totalling at least six foul events, because a
    two-leg ticket at even money is not what anyone opens a page like this for.
    Among those, the pick is the one furthest from what the other four say:
    a number everyone agrees on is a consensus, and gives no reason to prefer
    the character offering it.
    """
    best = None
    for cid, tiers in by_character.items():
        for slip in tiers:
            total = sum(leg["fouls"] for leg in slip["legs"])
            if total < MIN_TOTAL_FOULS or slip["probability"] < MIN_PICK_PROBABILITY:
                continue
            gap = sum(leg["prob"] - leg["packProb"] for leg in slip["legs"]) / len(slip["legs"])
            if best is None or gap > best["gap"]:
                best = {
                    "character": cid,
                    "tier": slip["targetLabel"],
                    "odds": slip["actualOdds"],
                    "outOf100": slip["outOf100"],
                    "totalFouls": total,
                    "gap": round(gap, 4),
                    "legs": [
                        {
                            "player": leg["player"],
                            "fouls": leg["fouls"],
                            "market": leg["market"],
                            "outOf100": leg["outOf100"],
                        }
                        for leg in slip["legs"]
                    ],
                }
    return best


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
