"""The house number, the fixed slates, and the table that scores them.

Two things live here because they answer the same objection.

**The house number** is the five averaged. Each is wrong in its own direction
and the errors are not perfectly correlated, so some of it cancels. It is a
sixth opinion, not a judge of the other five, which is what makes it the right
thing to put on a fixture card where there is room for one number.

**The table** exists because comparing characters on bets they chose themselves
measures difficulty, not judgement. A cautious one looks good by picking
near-certainties and a bold one looks bad by reaching. So every gameweek all
five commit to the same three shapes, and the only thing that varies is which
players they pick. That is the thing worth measuring.

Scored as football, which is the right metaphor for a site about football:
every leg lands is a win, all but one is a draw, anything worse is a loss, and
goal difference is legs landed minus legs missed.
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
    """Each character's committed bet at each fixed shape.

    Returns `{character: {slate_key: {"legs": [...]} | None}}`. A slate that
    cannot be filled from the pool comes back as None rather than short:
    committing to a shape you could not build is worse than passing, because it
    would be scored against everyone else's full one.
    """
    out: dict[str, dict] = {}

    for cid in character_ids:
        ranked = sorted(candidates, key=lambda r: -_preference(cid, r))
        out[cid] = {}

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

            out[cid][slate.key] = {"legs": legs, "label": slate.label} if ok else None

    return out


def join_slates(graded: list[dict], committed: list[dict]) -> list[dict]:
    """Pair graded claims with the slates that selected them.

    Grading keeps what it needs to score a probability and drops the rest, so a
    graded row cannot say which slate it belonged to. The slate store holds the
    claim keys it selected, and graded rows carry the same key, so the two join
    on it.

    Also normalises `won` to `landed`. Two names for one fact is how a table
    ends up silently empty.
    """
    outcome = {row["key"]: bool(row.get("won")) for row in graded if "key" in row}

    out = []
    for slate in committed:
        for claim_key in slate.get("claim_keys", []):
            if claim_key not in outcome:
                continue  # not settled yet, and an unsettled leg is not a miss
            out.append(
                {
                    "key": claim_key,
                    "model_id": slate["character"],
                    "landed": outcome[claim_key],
                    "extra": {"slate": slate["slate"]},
                }
            )
    return out


def table(graded: list[dict], character_ids: list[str]) -> list[dict]:
    """Standings from graded slate legs.

    A slate is only scored once EVERY leg has an outcome. Grading a half-settled
    slate would count its unsettled legs as misses, turning "we do not know yet"
    into "they got it wrong", which is the single easiest way to publish a track
    record that is quietly false.
    """
    # (character, slate) -> the legs graded so far
    by_slate: dict[tuple[str, str], list[bool]] = {}
    for row in graded:
        cid = row.get("model_id")
        slate = (row.get("extra") or {}).get("slate")
        if not cid or not slate or "landed" not in row:
            continue
        by_slate.setdefault((cid, slate), []).append(bool(row["landed"]))

    rows = []
    for cid in character_ids:
        played = won = drawn = lost = points = difference = 0
        landed_total = missed_total = 0

        for slate in ensemble.SLATES:
            legs = by_slate.get((cid, slate.key))
            if not legs or len(legs) != slate.legs:
                continue  # not every leg has settled, so it is not a result yet

            score = ensemble.score_slate(legs)
            played += 1
            points += score["points"]
            difference += score["difference"]
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
