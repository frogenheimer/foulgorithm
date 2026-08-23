"""Why each character backed each pick, said the way that character talks.

A published probability with nothing beside it asks the reader to trust a
number from a model they cannot inspect. This turns the same `why` block the
number came from into one or two sentences, so the words cannot drift away from
the maths: if the sentence says the matchup drove it, the matchup drove it.

The generation is deliberately dull underneath. Rank the drivers by how far
each sits from its neutral value, take the strongest one the character actually
cares about, and phrase it in their register. Character lives in the phrasing.
It is never allowed into the facts, which is the whole point: five voices
reading one set of numbers is a bake-off, five voices inventing their own
numbers is a puppet show.

Two rules the tests enforce:

  - Every claim traces to a figure in `why`.
  - Thin evidence gets said out loud in every voice. Terror frets about it,
    Bravery relishes it, and neither may quietly drop it.
"""

from __future__ import annotations

from foulgorithm.characters.base import BY_ID

#: Below this, a per-90 rate rests on too little playing time to lean on.
#:
#: Must match THIN_EVIDENCE in publish/player_round.py, which is what actually
#: sets the flag. When these disagreed at 5.0 against 8.0, a genuinely thin pick
#: with 5.2 matches was described as an unmatchable record instead, because the
#: only way to tell the two causes apart here is the match count. A test pins
#: them together.
THIN_MATCHES = 8.0

#: How far a multiplier must sit from 1.0 before it is worth a sentence.
NOTABLE = 0.08

#: Probability gap against the other four that counts as standing apart.
APART = 0.05


def _minutes_phrase(why: dict) -> tuple[str, bool]:
    """Playing time, and whether he is expected to start.

    Worth its own helper because describing a substitute as a starter is the
    quickest way to make the whole sentence false.
    """
    start = float(why.get("startProbability") or 0.0)
    minutes = round(float(why.get("expectedMinutes") or 0.0))
    return f"{minutes} minutes", start >= 0.6


def _drivers(leg: dict, why: dict) -> dict:
    """Everything worth mentioning, with a magnitude on each.

    Neutral is 1.0 for the multipliers, so distance from 1.0 is the signal.
    """
    rate = float(why.get("ratePer90") or 0.0)
    matches = float(why.get("effectiveMatches") or 0.0)
    opponent = float(why.get("opponentFactor") or 1.0)
    referee = float(why.get("refereeFactor") or 1.0)
    h2h = float(why.get("headToHeadFactor") or 1.0)
    edge = float(leg.get("edge") or 0.0)

    return {
        "rate": rate,
        "matches": matches,
        "opponent": opponent,
        "referee": referee,
        "h2h": h2h,
        "edge": edge,
        # Two different problems share one flag upstream: too little playing
        # time, and a record we could not match to the player at all. Saying
        # "only 65 matches, not enough" about the second is simply false, so
        # they are separated here.
        "thin": bool(leg.get("thin")) or matches < THIN_MATCHES,
        "thin_volume": matches < THIN_MATCHES,
        "unmatched": bool(leg.get("thin")) and matches >= THIN_MATCHES,
        "prob": float(leg.get("prob") or 0.0),
        "pack": float(leg.get("packProb") or 0.0),
        "fouls": int(leg.get("fouls") or 1),
        "market": leg.get("market") or "committed",
        "player": leg.get("player") or "He",
    }


def _verb(market: str, plural: bool = False) -> str:
    """Fouls committed and fouls won are opposite claims about the same player."""
    if market == "drawn":
        return "wins" if not plural else "win"
    if market == "involvements":
        return "is involved in" if not plural else "are involved in"
    return "commits" if not plural else "commit"


def _noun(market: str, n: int) -> str:
    thing = "foul" if n == 1 else "fouls"
    if market == "drawn":
        return f"{n} {thing} won"
    if market == "involvements":
        return f"{n} foul involvement" if n == 1 else f"{n} foul involvements"
    return f"{n} {thing}"


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _matches_phrase(d: dict) -> str:
    """How much evidence, in words that survive very small numbers.

    "0 matches" is what 0.2 effective matches rounds to, and it reads as though
    the player has never played. Under one, say so in words instead.
    """
    n = d["matches"]
    if n < 1:
        return "barely a match of recent evidence"
    if n < 10:
        return f"{n:.1f} matches"
    return f"{n:.0f} matches"


# ---------------------------------------------------------------------------
# The five voices.
#
# Each takes the same driver dict and returns one or two sentences. They are
# hand-written rather than templated from a shared skeleton on purpose: a
# shared skeleton produces five sentences with the adjectives swapped, which
# reads as a gimmick within about four cards.
# ---------------------------------------------------------------------------


def _alan(d: dict, why: dict) -> str:
    """Anger. Clipped, certain, contemptuous of context. Never more than two lines."""
    minutes, starting = _minutes_phrase(why)

    if d["unmatched"]:
        return f"His record will not join up cleanly. {_pct(d['prob'])} anyway."
    if d["thin"]:
        return (
            f"{_matches_phrase(d).capitalize()} and I do not care. "
            f"{_pct(d['prob'])} says {_noun(d['market'], d['fouls'])}."
        )
    if d["edge"] >= APART:
        return (
            f"{d['rate']:.2f} a game. The other four have him at {_pct(d['pack'])} "
            f"and they are being soft about it."
        )
    if d["opponent"] >= 1 + NOTABLE:
        return f"{d['rate']:.2f} a game into a fixture that drags it up. Obvious."
    if not starting:
        return f"Only {minutes} of him, and he still {_verb(d['market'])} at {d['rate']:.2f} a game."
    return f"{d['rate']:.2f} a game over {minutes}. That is not a phase, that is the player."


def _lily(d: dict, why: dict) -> str:
    """Lust. Appetite, indulgence, drawn to the big number and the big name."""
    minutes, starting = _minutes_phrase(why)

    if d["unmatched"]:
        return (
            f"His history refuses to line up neatly, which only makes him more "
            f"interesting. {d['rate']:.2f} a game in what does match."
        )
    if d["thin"]:
        return (
            f"Almost nothing on him, {_matches_phrase(d)}, and {d['rate']:.2f} a game "
            f"in what there is. New things are the best things."
        )
    if d["rate"] >= 1.6:
        return (
            f"{d['rate']:.2f} a game is a lovely number and I am not going to pretend "
            f"otherwise. {minutes} to enjoy it."
        )
    if d["opponent"] >= 1 + NOTABLE:
        return (
            f"This fixture pulls him up {_pct(d['opponent'] - 1)} above his own rate. "
            f"The occasion does half the work."
        )
    if not starting:
        return f"Only {minutes}, which is a shame, because {d['rate']:.2f} a game deserves more."
    return f"{d['rate']:.2f} a game across {minutes}, and {_pct(d['prob'])} of it landing. Yes."


def _valentina(d: dict, why: dict) -> str:
    """Violence. Reads the fixture as a confrontation and says so."""
    minutes, starting = _minutes_phrase(why)

    if d["unmatched"]:
        return (
            f"His own record is a mess to trace, so I am reading the fixture instead: "
            f"{_pct(d['prob'])}."
        )
    if d["thin"]:
        return (
            f"{_matches_phrase(d).capitalize()} of him, which tells me little. The fixture "
            f"tells me more, and it says {_pct(d['prob'])}."
        )
    if d["opponent"] >= 1 + NOTABLE:
        return (
            f"This opposition drags fouls out of people, {_pct(d['opponent'] - 1)} above "
            f"the usual. He is walking into it for {minutes}."
        )
    if d["h2h"] >= 1 + NOTABLE:
        return (
            f"These two have history: {_pct(d['h2h'] - 1)} more than either side's record "
            f"implies on its own. It gets ugly."
        )
    if d["referee"] >= 1 + NOTABLE:
        return (
            f"A referee who gives {_pct(d['referee'] - 1)} more than most. "
            f"Every challenge gets counted today."
        )
    if not starting:
        return f"{minutes} is enough time to get into something at {d['rate']:.2f} a game."
    return f"A flat fixture on paper, so it comes down to him: {d['rate']:.2f} a game."


def _tayler(d: dict, why: dict) -> str:
    """Terror. Anxious, qualified, reassured only by volume and agreement."""
    minutes, starting = _minutes_phrase(why)

    if d["unmatched"]:
        return (
            f"I cannot match his record cleanly, which is its own kind of risk, "
            f"but {_pct(d['prob'])} still clears my floor. Reluctantly."
        )
    if d["thin"]:
        return (
            f"Only {_matches_phrase(d)} behind this, which is not enough, "
            f"but {_pct(d['prob'])} still clears my floor. I am not comfortable."
        )
    if abs(d["edge"]) < 0.02:
        return (
            f"{d['matches']:.0f} matches of evidence and the other four land within a point "
            f"of me. Agreement is the most reassuring thing here."
        )
    if d["edge"] < -APART:
        return (
            f"I have him lower than the rest, {_pct(d['prob'])} against their "
            f"{_pct(d['pack'])}, which is usually where I would rather be."
        )
    if not starting:
        return (
            f"Only {minutes} expected, which is the part that worries me, "
            f"though {d['matches']:.0f} matches say the rate holds."
        )
    return (
        f"{d['matches']:.0f} matches behind it and {minutes} expected, which is enough "
        f"to be dull at {_pct(d['prob'])}. Dull is the most I ever want."
    )


def _bdog(d: dict, why: dict) -> str:
    """Bravery. Defines itself against the other four and says so out loud."""
    minutes, starting = _minutes_phrase(why)

    if d["unmatched"]:
        return (
            f"Nobody can trace his record properly, so the rest sit at {_pct(d['pack'])}. "
            f"That is where being alone pays."
        )
    if d["thin"]:
        return (
            f"{_matches_phrase(d).capitalize()} is exactly the evidence the others shrink "
            f"away, and the rest have him at {_pct(d['pack'])}. Someone has to be first."
        )
    if d["edge"] >= APART:
        return (
            f"Everyone else has him at {_pct(d['pack'])}. I have him at {_pct(d['prob'])}. "
            f"One of us is wrong and I am comfortable being alone on it."
        )
    if d["edge"] <= -APART:
        return (
            f"The pack is at {_pct(d['pack'])} and I am under it at {_pct(d['prob'])}. "
            f"Being the only one out is the position worth holding."
        )
    if not starting:
        return (
            f"{minutes} off the bench and nobody wants it. "
            f"{d['rate']:.2f} a game says they should."
        )
    return (
        f"The rest are within a point of me here, which is the least interesting "
        f"place to be. {d['rate']:.2f} a game carries it."
    )


_VOICES = {
    "alan": _alan,
    "lily": _lily,
    "valentina": _valentina,
    "tayler": _tayler,
    "bdog": _bdog,
}


def reason(character_id: str, leg: dict, why: dict) -> str:
    """One or two sentences on why this character backed this pick.

    Raises on an unknown character rather than falling back to a neutral voice,
    because a neutral voice attributed to a named character is a lie about who
    said it.
    """
    if character_id not in _VOICES:
        raise KeyError(f"unknown character {character_id!r}. Known: {sorted(_VOICES)}")
    return _VOICES[character_id](_drivers(leg, why), why)


def summary(character_id: str, legs: list[dict]) -> str:
    """One line about a whole slip, rather than one line per leg.

    A slip is a single claim: all of these, or nothing. The card should say what
    the character thinks of it as a unit before it lists the parts.
    """
    c = BY_ID[character_id] if character_id in BY_ID else None
    if c is None:
        raise KeyError(f"unknown character {character_id!r}")
    if not legs:
        return "Nothing here worth the risk."

    n = len(legs)
    thin = sum(1 for leg in legs if leg.get("thin"))
    bold = sum(1 for leg in legs if float(leg.get("edge") or 0) >= APART)

    if character_id == "alan":
        return f"{n} of them, and every one of us knows it. No hedging."
    if character_id == "lily":
        return f"{n} names I actually want, not {n} names that merely add up."
    if character_id == "valentina":
        return f"{n} players walking into fixtures that are going to get physical."
    if character_id == "tayler":
        extra = f" {thin} of them thinner than I would like." if thin else ""
        return f"{n} legs, which is {n} chances to be wrong.{extra}"
    return f"{n} legs, {bold} of them against what the other four think. That is the point."
