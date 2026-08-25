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

from foulgorithm.models import ensemble


def house_probability(row: dict, character_ids: list[str]) -> float:
    """The blended number for one candidate bet."""
    probs = [row["probs"][c] for c in character_ids if c in row.get("probs", {})]
    return ensemble.blend(probs)


def _preference(cid: str, row: dict) -> float:
    """How much this character wants this bet.

    Deliberately the same idea as the slip builder: boldness is distance from
    what the other four think, never a lower probability. A character backing a
    70% shot the rest price at 55% is being bold; one backing a 45% shot
    everybody agrees on has only accepted a longer price.
    """
    from foulgorithm.publish.player_round import _preference as slip_preference

    return slip_preference(cid, row)


def build_slates(candidates: list[dict], character_ids: list[str]) -> dict:
    """Each character's three bets, per game. The contract; see docs/38.

    Returns `{fixture: {character: {slate_key: {"legs": [...]} | None}}}`.
    Every game gets its own three shapes from every character, built only
    from that game's players, so 30 bets per character per ten-game week. A
    slate that cannot be filled from one game's pool comes back as None
    rather than short: committing to a shape you could not build is worse
    than passing, because it would be scored against everyone else's full
    one.
    """
    by_game: dict[str, list[dict]] = {}
    for row in candidates:
        by_game.setdefault(row["fixture"], []).append(row)

    out: dict[str, dict] = {}
    for label in sorted(by_game):
        pool = by_game[label]
        out[label] = {}
        for cid in character_ids:
            ranked = sorted(pool, key=lambda r: -_preference(cid, r))
            own: dict[str, dict | None] = {}

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
                            {
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
                        )

                own[slate.key] = {"legs": legs, "label": slate.label} if ok else None
            out[label][cid] = own

    return out


def round_id(row: dict) -> str:
    """Which round a slate version belongs to: the date of its own first
    kickoff, never the stored label.

    The stored round label was week-based, and week keys collide: the night
    of 2026-08-24 a round finished on the Monday and the next was published
    under the same key two hours later, superseding picks nobody ever
    re-made. The kickoff each row carries identifies its round unambiguously.
    Rows from before the field existed fall back to the label.
    """
    kickoff = row.get("first_kickoff") or ""
    return kickoff[:10] or row.get("round", "")


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
        key = (
            f"{round_id(row)}|{row['character']}|{row['slate']}|{row.get('fixture') or ''}"
        )
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
        if round_key and round_key < since:
            continue
        landed = bool(row["landed"])
        deficit = int(row.get("deficit") or (0 if landed else 1))
        key = (round_key, extra.get("fixture") or "", cid, slate)
        by_slate.setdefault(key, []).append((landed, deficit))
        if extra.get("expected") is not None:
            expected[key] = int(extra["expected"])

    shape_legs = {sl.key: sl.legs for sl in ensemble.SLATES}

    rows = []
    for cid in character_ids:
        played = won = drawn = lost = points = difference = 0
        landed_total = missed_total = 0

        for key, pairs in by_slate.items():
            round_key, _fixture, owner, slate_key = key
            if owner != cid:
                continue
            need = expected.get(key, shape_legs.get(slate_key, 0))
            if not pairs or need == 0 or len(pairs) != need:
                continue  # not every leg has settled, so it is not a result yet

            score = ensemble.score_slate([landed for landed, _ in pairs])
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
