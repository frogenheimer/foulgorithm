"""The house number, the fixed slates, and the table that scores them.

Two things live here because they answer the same objection.

**The house number** is the five averaged. Each is wrong in its own direction
and the errors are not perfectly correlated, so some of it cancels. It is a
sixth opinion, not a judge of the other five, which is what makes it the right
thing to put on a fixture card where there is room for one number.

**The table** exists because comparing characters on bets they chose themselves
measures difficulty, not judgement. A cautious one looks good by picking
near-certainties and a bold one looks bad by reaching. So on every game all
five commit to the same three shapes (docs/38), and the only thing that
varies is which players they pick. That is the thing worth measuring.

Scored as football, which is the right metaphor for a site about football:
every leg lands is a win, all but one is a draw, anything worse is a loss. The
difference column is FOUL difference, and it carries the size of a miss: a 2+
shout where he never fouled counts -2, missed by one counts -1, and a landed
leg counts +1. A near miss and a nowhere miss stop looking the same.
"""

from __future__ import annotations

import math

from foulgorithm.models import ensemble


def house_probability(row: dict, character_ids: list[str]) -> float:
    """The blended number for one candidate bet."""
    probs = [row["probs"][c] for c in character_ids if c in row.get("probs", {})]
    return ensemble.blend(probs)


def _preference(cid: str, row: dict, context: dict | None = None) -> float:
    """How much this character wants this bet.

    Deliberately the same function as the slip builder, so a character's
    taste is one thing everywhere: logic first, temperament clamped to each
    character's sway (docs/38, unified 2026-08-25).
    """
    from foulgorithm.publish.player_round import _preference as slip_preference

    return slip_preference(cid, row, context)


def _edge(cid: str, row: dict) -> float:
    """How far this character's number sits above the pack's on one leg."""
    own = row["probs"][cid]
    others = [p for c, p in row["probs"].items() if c != cid]
    return own - (sum(others) / len(others)) if others else 0.0


def _leg_from_row(row: dict, cid: str, hot: bool | None = None) -> dict:
    leg = {
        "player": row["player"],
        "fullName": row["fullName"],
        "team": row["team"],
        "fixture": row["fixture"],
        "kickoff": row["kickoff"],
        "market": row["market"],
        "line": row["line"],
        "fouls": int(row["line"] + 0.5),
        "prob": round(row["probs"][cid], 4),
        "outOf100": round(row["probs"][cid] * 100),
        "thin": bool(row.get("thin")),
    }
    if hot is not None:
        leg["hotTake"] = hot
    return leg


def _hot_take_floor(cid: str, own: dict, pool: list[dict], context: dict | None) -> None:
    """Guarantee every character's one genuine disagreement per game (docs/38).

    A floor, never a cap: a draft already carrying a hot take is untouched,
    and extra hot takes are welcome. Only when every leg across the three
    bets is consensus does the character's single strongest disagreement
    swap in, replacing the least-wanted leg at the same line in the same
    bet, so the shapes stay exactly what they promise.
    """
    from foulgorithm.publish.player_round import HOT_TAKE_MARGIN

    if any(
        leg.get("hotTake")
        for built in own.values()
        if built
        for leg in built["legs"]
    ):
        return

    mavericks = sorted(
        (r for r in pool if r.get("probs", {}).get(cid) is not None and _edge(cid, r) >= HOT_TAKE_MARGIN),
        key=lambda r: -_edge(cid, r),
    )
    for row in mavericks:
        for built in own.values():
            if not built:
                continue
            used = {leg["fullName"] for leg in built["legs"]}
            if row["fullName"] in used:
                continue
            replaceable = [
                i
                for i, leg in enumerate(built["legs"])
                if leg["line"] == row["line"]
            ]
            if not replaceable:
                continue
            weakest = min(
                replaceable,
                key=lambda i: _preference(cid, _row_for(built["legs"][i], pool, cid), context)
                if _row_for(built["legs"][i], pool, cid)
                else 0.0,
            )
            swapped = _leg_from_row(row, cid, hot=True)
            if "houseProb" in built["legs"][weakest]:
                swapped["houseProb"] = round(_house_price(row), 4)
            built["legs"][weakest] = swapped
            return


def _row_for(leg: dict, pool: list[dict], cid: str) -> dict | None:
    for row in pool:
        if (
            row["fullName"] == leg["fullName"]
            and row["market"] == leg["market"]
            and row["line"] == leg["line"]
        ):
            return row
    return None


def _house_price(row: dict) -> float:
    """The house's own number for one leg: the ruler every band is measured by."""
    from foulgorithm.publish.player_round import HOUSE_MODEL

    probs = row.get("probs") or {}
    if HOUSE_MODEL in probs:
        return float(probs[HOUSE_MODEL])
    return house_probability(row, list(probs))


def _priced_bet(cid: str, ranked: list[dict], band, context: dict | None) -> dict | None:
    """One bet inside a band, by the house's price, in this character's order.

    Legs join in the character's own preference order until the house prices
    the bet inside the band. Two rules keep that reachable. A leg that would
    drop the bet BELOW the band is skipped for a milder one further down. And
    a leg only joins as a filler if the band is still reachable after it
    within six legs, using the smallest prices left in the pool; otherwise
    the builder reaches for a bigger leg now. Whenever one remaining leg
    would land the bet in the band outright, the most-preferred such leg
    closes it. Two to six legs; None when the pool cannot make the price.
    """
    from foulgorithm.publish.player_round import HOT_TAKE_MARGIN, MAX_LEGS_PER_TIER

    rows = [r for r in ranked if cid in r.get("probs", {}) and _house_price(r) > 0]
    chosen: list[dict] = []
    used: set[str] = set()
    combined = 1.0

    def smallest_per_player(excluding: str) -> list[float]:
        best: dict[str, float] = {}
        for r in rows:
            name = r["fullName"]
            if name in used or name == excluding:
                continue
            p = _house_price(r)
            if name not in best or p < best[name]:
                best[name] = p
        return sorted(best.values())

    def reachable(after: float, excluding: str) -> bool:
        slots = MAX_LEGS_PER_TIER - len(chosen) - 1
        return after * math.prod(smallest_per_player(excluding)[:slots]) <= band.high

    while len(chosen) < MAX_LEGS_PER_TIER:
        # The character's next preference, so long as it neither drops the
        # bet below the band nor leaves the band unreachable in the legs that
        # remain. That is what lets a cautious character reach a price with
        # five small legs and a bold one with two big ones.
        pick = next(
            (
                r
                for r in rows
                if r["fullName"] not in used
                and combined * _house_price(r) >= band.low
                and reachable(combined * _house_price(r), r["fullName"])
            ),
            None,
        )
        if pick is None:
            # Nothing preferred fits: the last resort is any leg that lands
            # the bet in the band outright.
            pick = next(
                (
                    r
                    for r in rows
                    if r["fullName"] not in used
                    and band.low <= combined * _house_price(r) <= band.high
                ),
                None,
            )
            if pick is None:
                return None
        chosen.append(pick)
        used.add(pick["fullName"])
        combined *= _house_price(pick)
        if combined <= band.high and len(chosen) >= 2:
            break

    if len(chosen) < 2 or not (band.low <= combined <= band.high):
        return None

    legs = []
    for row in chosen:
        leg = _leg_from_row(row, cid, hot=_edge(cid, row) >= HOT_TAKE_MARGIN)
        leg["houseProb"] = round(_house_price(row), 4)
        legs.append(leg)
    return {
        "legs": legs,
        "label": band.label,
        "band": band.key,
        "housePrice": round(combined, 4),
        "target": band.target,
    }


def _in_band(bet: dict | None) -> bool:
    if not bet:
        return True
    band = next((b for b in ensemble.BANDS if b.key == bet.get("band")), None)
    if band is None:
        return True
    price = 1.0
    for leg in bet["legs"]:
        price *= leg.get("houseProb", 1.0)
    return band.low <= price <= band.high


def build_slates(
    candidates: list[dict], character_ids: list[str], context: dict | None = None
) -> dict:
    """Each character's three bets, per game. The contract; see docs/38.

    Returns `{fixture: {character: {slate_key: {"legs": [...]} | None}}}`.
    Every game gets its own three shapes from every character, built only
    from that game's players, so 30 bets per character per ten-game week. A
    slate that cannot be filled from one game's pool comes back as None
    rather than short: committing to a shape you could not build is worse
    than passing, because it would be scored against everyone else's full
    one. Every character carries the hot-take floor (docs/38, unified
    2026-08-25), and legs are flagged wherever a character genuinely parts
    company with the pack.
    """
    from foulgorithm.publish.player_round import HOT_TAKE_MARGIN

    by_game: dict[str, list[dict]] = {}
    for row in candidates:
        by_game.setdefault(row["fixture"], []).append(row)

    out: dict[str, dict] = {}
    for label in sorted(by_game):
        pool = by_game[label]
        out[label] = {}
        for cid in character_ids:
            ranked = sorted(pool, key=lambda r: -_preference(cid, r, context))
            own: dict[str, dict | None] = {}

            if ensemble.priced(pool[0]["kickoff"]):
                # docs/42: three bets at three house-priced bands, shape free.
                # Ranked by EDGE over the house, not by raw probability: a
                # character hunts the legs it believes the house underprices,
                # which is where a 2+ shout it is bullish on outranks a 1+ it
                # merely agrees with. Ranking by probability alone walked
                # every character down the 1+ list and made every layout the
                # same. Temperament rides in through the preference's lean.
                hunted = sorted(
                    pool,
                    key=lambda r: (
                        -(_preference(cid, r, context) - _house_price(r)),
                        -_preference(cid, r, context),
                    ),
                )
                for band in ensemble.BANDS:
                    own[band.key] = _priced_bet(cid, hunted, band, context)
                before = {k: (dict(v, legs=list(v["legs"])) if v else None) for k, v in own.items()}
                _hot_take_floor(cid, own, pool, context)
                # The floor swaps a leg at the same line, which can move the
                # house price out of the band. A bet the floor pushed out of
                # its band goes back to how it was: the price is the contract.
                for key, bet in own.items():
                    if not _in_band(bet):
                        own[key] = before[key]
                    elif bet:
                        bet["housePrice"] = round(
                            math.prod(leg.get("houseProb", 1.0) for leg in bet["legs"]), 4
                        )
                out[label][cid] = own
                continue

            for slate in ensemble.SLATES:
                legs: list[dict] = []
                used: set[str] = set()
                ok = True

                for line, count in slate.shape:
                    at_line = [
                        r
                        for r in ranked
                        if r["line"] == line and r["fullName"] not in used and cid in r["probs"]
                    ]
                    if len(at_line) < count:
                        ok = False
                        break
                    for row in at_line[:count]:
                        used.add(row["fullName"])
                        legs.append(
                            _leg_from_row(row, cid, hot=_edge(cid, row) >= HOT_TAKE_MARGIN)
                        )

                own[slate.key] = {"legs": legs, "label": slate.label} if ok else None

            _hot_take_floor(cid, own, pool, context)
            out[label][cid] = own

    return out


def round_id(row: dict) -> str:
    """Which round a bet belongs to: the league's own gameweek.

    Rows committed since 2026-08-25 carry the fixture's matchweek and get a
    gameweek id ("mw02"). Older rows fall back to the date of their round's
    first kickoff, and the oldest to their stored label. Never trust the
    stored label alone: week-based labels collided on 2026-08-24 and a new
    round superseded picks nobody ever re-made.
    """
    matchweek = row.get("matchweek")
    if matchweek:
        return f"mw{int(matchweek):02d}"
    kickoff = row.get("first_kickoff") or ""
    return kickoff[:10] or row.get("round", "")


def round_before(round_key: str, since: str) -> bool:
    """The season filter, across both round-id generations.

    Gameweek ids ("mw02") only exist under the docs/38 contract and are
    never before the season start; legacy date ids compare as dates.
    """
    if round_key.startswith("mw"):
        return False
    return bool(round_key) and round_key < since


def binding_versions(committed: list[dict]) -> list[dict]:
    """One row per bet: the latest version published before its own kickoff.

    Slates version rather than mutate, so a lineup-time re-publish appends a
    fresh row for the same key. The one that counts is the last committed
    before the bet's own game kicks off: after that moment results have
    started arriving, and a version published then is recorded and ignored,
    because replacing a bet once outcomes exist is cherry-picking with extra
    steps. Per-game bets cut off at their OWN kickoff, so a Saturday bet
    still regenerates at T-60 after Friday's game has started; round-wide
    rows from before docs/38 cut off at the round's first kickoff, and rows
    from before that field existed were all pre-kickoff by construction.
    Rounds are told apart by round_id, not by the stored key, so a new round
    never supersedes the old one's picks.
    """
    eligible: dict[str, dict] = {}
    for row in committed:
        cutoff = row.get("kickoff") or row.get("first_kickoff")
        published = row.get("published_at", "")
        if cutoff and published > cutoff:
            continue
        # A per-game bet's identity is the game itself (unique within a
        # season), never the publish moment: a Saturday republish used to
        # mint a fresh round key and the same bet bound twice. The kickoff
        # year keeps identities apart across seasons.
        fixture = row.get("fixture")
        if fixture:
            year = (row.get("kickoff") or row.get("first_kickoff") or "")[:4]
            key = f"{row['character']}|{row['slate']}|{fixture}|{year}"
        else:
            key = f"{round_id(row)}|{row['character']}|{row['slate']}|"
        held = eligible.get(key)
        if held is None or published > held.get("published_at", ""):
            eligible[key] = row
    return list(eligible.values())


def join_slates(
    graded: list[dict], committed: list[dict], completed: set[str] | None = None
) -> list[dict]:
    """Pair graded claims with the bets that selected them.

    Grading keeps what it needs to score a probability and drops the rest, so a
    graded row cannot say which slate it belonged to. The slate store holds the
    claim keys it selected, and graded rows carry the same key, so the two join
    on it. Only the binding version of each slate joins; see binding_versions.

    The void backstop: when a bet's game is in `completed` and a leg still has
    no graded outcome (a fetch failure, a player who never appeared), the leg
    voids and the bet settles on its remaining legs. Every emitted row carries
    the bet's EXPECTED leg count after voids, so the table knows when a bet is
    fully settled without guessing. "Open" is never a permanent state.

    Also normalises `won` to `landed`. Two names for one fact is how a table
    ends up silently empty.
    """
    outcome: dict[str, dict] = {}
    for row in graded:
        if "key" not in row:
            continue
        landed = bool(row.get("won"))
        # How far a miss missed by, in fouls. A 2+ shout where he never
        # fouled is a worse read than one where he fouled once, and the
        # difference column should say so. Landed legs carry zero; a graded
        # row without its counts falls back to one, the old flat scoring.
        deficit = 0
        if not landed and row.get("line") is not None and row.get("observed") is not None:
            needed = int(float(row["line"]) + 0.5)
            deficit = max(needed - int(float(row["observed"])), 1)
        elif not landed:
            deficit = 1
        outcome[row["key"]] = {"landed": landed, "deficit": deficit}

    out = []
    for slate in binding_versions(committed):
        claim_keys = slate.get("claim_keys", [])
        fixture = slate.get("fixture")
        game_over = bool(completed) and fixture in (completed or set())
        voided = sum(1 for k in claim_keys if k not in outcome) if game_over else 0
        expected = len(claim_keys) - voided
        for claim_key in claim_keys:
            if claim_key not in outcome:
                continue  # not settled yet, and an unsettled leg is not a miss
            graded_leg = outcome[claim_key]
            out.append(
                {
                    "key": claim_key,
                    "model_id": slate["character"],
                    "landed": graded_leg["landed"],
                    "deficit": graded_leg["deficit"],
                    "extra": {
                        "slate": slate["slate"],
                        "round": round_id(slate),
                        "fixture": fixture,
                        "expected": expected,
                    },
                }
            )
    return out


def boldness(
    committed: list[dict],
    graded: list[dict],
    predictions: list[dict],
    character_ids: list[str],
    since: str = None,
) -> dict[str, dict]:
    """How rare each character's picks are, by the house's own price.

    Oliver's call, 2026-08-26: a landed longshot deserves more credit than a
    landed banker, and the judge of rarity is the house number published
    before kickoff, never the character's own. Two figures per character:
    `boldness`, the average rarity of every BINDING pick this season,
    settled or not, so a timid book reads timid while it waits; and
    `winBoldness`, rarity banked only when the pick lands, which breaks
    league-table ties behind foul difference. Neither ever awards points:
    the shape of the league stays wins, draws and losses.
    """
    since = since if since is not None else SEASON_START
    by_key = {p["key"]: p for p in predictions if "key" in p}

    house: dict[tuple, dict] = {}
    for p in predictions:
        if p.get("model_id") != "house":
            continue
        ident = (p.get("fixture"), p.get("entity"), p.get("market"), p.get("line"))
        held = house.get(ident)
        if held is None or p.get("published_at", "") > held.get("published_at", ""):
            house[ident] = p

    landed = {g["key"] for g in graded if g.get("won")}

    tally = {cid: {"n": 0, "total": 0.0, "wins": 0.0} for cid in character_ids}
    for slate in binding_versions(committed):
        if round_before(round_id(slate), since):
            continue
        cid = slate.get("character")
        if cid not in tally:
            continue
        for key in slate.get("claim_keys", []):
            claim = by_key.get(key)
            if not claim:
                continue
            priced = house.get(
                (claim.get("fixture"), claim.get("entity"), claim.get("market"), claim.get("line"))
            )
            if not priced:
                continue
            rarity = 1.0 - float(priced.get("probability") or 0.0)
            tally[cid]["n"] += 1
            tally[cid]["total"] += rarity
            if key in landed:
                tally[cid]["wins"] += rarity

    return {
        cid: {
            "boldness": round(v["total"] / v["n"], 3) if v["n"] else 0.0,
            "winBoldness": round(v["wins"], 2),
        }
        for cid, v in tally.items()
    }


#: The league's first round: the first one played under the three-bets-per-
#: game contract (docs/38). Everything committed before exists on file and
#: stays graded in the raw record, but it was a different shape of bet
#: (round-wide slates), and a table mixing the two would mean nothing.
#: Oliver's call, 2026-08-25.
SEASON_START = "2026-08-28"


def table(
    graded: list[dict], character_ids: list[str], since: str = SEASON_START
) -> list[dict]:
    """Standings from graded slate legs.

    A slate is only scored once EVERY leg has an outcome. Grading a half-settled
    slate would count its unsettled legs as misses, turning "we do not know yet"
    into "they got it wrong", which is the single easiest way to publish a track
    record that is quietly false.

    Grouped by ROUND and GAME as well as shape, because the same character
    plays the same three shapes on every game: without both in the key, legs
    from two different bets pooled into one bucket and could score as a bet
    that nobody ever committed.
    """
    # (round, fixture, character, slate) -> (landed, deficit) per leg graded
    by_slate: dict[tuple[str, str, str, str], list[tuple[bool, int]]] = {}
    # Same key -> how many legs this bet needs after voids. Absent means the
    # full shape (rows from before the void backstop existed).
    expected: dict[tuple[str, str, str, str], int] = {}
    for row in graded:
        cid = row.get("model_id")
        extra = row.get("extra") or {}
        slate = extra.get("slate")
        round_key = extra.get("round") or ""
        if not cid or not slate or "landed" not in row:
            continue
        if round_before(round_key, since):
            continue
        landed = bool(row["landed"])
        deficit = int(row.get("deficit") or (0 if landed else 1))
        key = (round_key, extra.get("fixture") or "", cid, slate)
        by_slate.setdefault(key, []).append((landed, deficit))
        if extra.get("expected") is not None:
            expected[key] = int(extra["expected"])

    shape_legs = {sl.key: sl.legs for sl in ensemble.SLATES}
    band_keys = {b.key for b in ensemble.BANDS}

    rows = []
    for cid in character_ids:
        played = won = drawn = lost = points = difference = 0
        landed_total = missed_total = 0

        for key, pairs in by_slate.items():
            round_key, _fixture, owner, slate_key = key
            if owner != cid:
                continue
            priced_bet = slate_key in band_keys
            need = expected.get(key, 0 if priced_bet else shape_legs.get(slate_key, 0))
            if not pairs or need == 0 or len(pairs) != need:
                continue  # not every leg has settled, so it is not a result yet
            if priced_bet and need < 2:
                continue  # voided below two legs: void whole, not a result (docs/42)

            score = (
                ensemble.score_priced(pairs)
                if priced_bet
                else ensemble.score_slate([landed for landed, _ in pairs])
            )
            played += 1
            points += score["points"]
            # Foul difference: +1 per landed leg, minus the size of each
            # miss. score_slate still decides the RESULT from the leg
            # count alone, so a heavy miss costs difference, never extra
            # points.
            difference += sum(1 if landed else -deficit for landed, deficit in pairs)
            landed_total += score["landed"]
            missed_total += score["missed"]
            won += score["result"] == "won"
            drawn += score["result"] == "drawn"
            lost += score["result"] == "lost"

        rows.append(
            {
                "id": cid,
                "played": played,
                "won": won,
                "drawn": drawn,
                "lost": lost,
                "legsLanded": landed_total,
                "legsMissed": missed_total,
                "difference": difference,
                "points": points,
            }
        )

    rows.sort(key=lambda r: (-r["points"], -r["difference"], -r["legsLanded"], r["id"]))
    return rows
