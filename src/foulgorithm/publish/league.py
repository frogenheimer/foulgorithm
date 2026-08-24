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


def binding_versions(committed: list[dict]) -> list[dict]:
    """One row per slate key: the latest version published before kickoff.

    Slates version rather than mutate, so a lineup-time re-publish appends a
    fresh row for the same key. The one that counts is the last committed
    before the round's first kickoff: after that moment results have started
    arriving, and a version published then is recorded and ignored, because
    replacing a slate once outcomes exist is cherry-picking with extra steps.
    Rows written before the field existed were all pre-kickoff by
    construction and stay eligible.
    """
    eligible: dict[str, dict] = {}
    for row in committed:
        first_kickoff = row.get("first_kickoff")
        published = row.get("published_at", "")
        if first_kickoff and published > first_kickoff:
            continue
        key = row.get("key") or f"{row.get('round', '')}|{row['character']}|{row['slate']}"
        held = eligible.get(key)
        if held is None or published > held.get("published_at", ""):
            eligible[key] = row
    return list(eligible.values())


def join_slates(graded: list[dict], committed: list[dict]) -> list[dict]:
    """Pair graded claims with the slates that selected them.

    Grading keeps what it needs to score a probability and drops the rest, so a
    graded row cannot say which slate it belonged to. The slate store holds the
    claim keys it selected, and graded rows carry the same key, so the two join
    on it. Only the binding version of each slate joins; see binding_versions.

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
        for claim_key in slate.get("claim_keys", []):
            if claim_key not in outcome:
                continue  # not settled yet, and an unsettled leg is not a miss
            graded_leg = outcome[claim_key]
            out.append(
                {
                    "key": claim_key,
                    "model_id": slate["character"],
                    "landed": graded_leg["landed"],
                    "deficit": graded_leg["deficit"],
                    "extra": {"slate": slate["slate"], "round": slate.get("round")},
                }
            )
    return out


#: The league's first round. Slates committed before this exist on file and
#: stay graded in the raw record, but the table starts here: the season opens
#: with the first round committed under the upgraded models, so every entry in
#: it was produced by the same generation of machinery. Oliver's call,
#: 2026-08-24.
SEASON_START = "2026-08-24"


def table(
    graded: list[dict], character_ids: list[str], since: str = SEASON_START
) -> list[dict]:
    """Standings from graded slate legs.

    A slate is only scored once EVERY leg has an outcome. Grading a half-settled
    slate would count its unsettled legs as misses, turning "we do not know yet"
    into "they got it wrong", which is the single easiest way to publish a track
    record that is quietly false.

    Grouped by ROUND as well as shape, because the same character plays the
    same three shapes every week: without the round in the key, legs from two
    different weeks pooled into one bucket, and three legs settling across two
    rounds could score as one slate that nobody ever committed.
    """
    # (round, character, slate) -> (landed, deficit) per leg graded so far
    by_slate: dict[tuple[str, str, str], list[tuple[bool, int]]] = {}
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
        by_slate.setdefault((round_key, cid, slate), []).append((landed, deficit))

    rounds = {round_key for round_key, _, _ in by_slate}

    rows = []
    for cid in character_ids:
        played = won = drawn = lost = points = difference = 0
        landed_total = missed_total = 0

        for round_key in rounds:
            for slate in ensemble.SLATES:
                pairs = by_slate.get((round_key, cid, slate.key))
                if not pairs or len(pairs) != slate.legs:
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
