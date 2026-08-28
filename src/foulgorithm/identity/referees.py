"""Match one official across three sources that spell him three ways.

  football-data.co.uk   "A Kitchen"
  API-Football          "Andrew Kitchen, England"
  the hand-fed slate    "Andrew Kitchen"

`features/match_features._referee_factor` compares `referee_raw` strings
exactly, so a cup tie carrying the long form has been matching nothing and
reporting it as an absent record rather than as a failed join. That is the
worst kind of gap: it looks like an honest "we do not know".

The join key is first-initial-plus-surname, because that is what football-data
already writes and it holds by far the most matches. Two officials sharing an
initial and a surname collapse into one, which is a real limit and is why
`CROSSWALK` exists to separate a collision by hand when one turns up.
"""

from __future__ import annotations

import re

#: Hand-resolved cases, checked before anything is derived. Left side is any
#: source's spelling, right side is the football-data key it belongs to.
CROSSWALK: dict[str, str] = {}

_COUNTRY_SUFFIX = re.compile(r",.*$")

#: Surname particles. These belong to the surname however they are capitalised,
#: so "Robert Van Der Berg" keys as "R Van Der Berg". Dropping them would merge
#: officials who share only the final word of their name.
_PARTICLES = {
    "van",
    "von",
    "de",
    "del",
    "della",
    "der",
    "den",
    "di",
    "da",
    "dos",
    "du",
    "la",
    "le",
    "mac",
    "mc",
    "st",
    "ter",
    "ten",
}


def _tokens(name: str) -> list[str]:
    cleaned = _COUNTRY_SUFFIX.sub("", name).replace(".", " ")
    return [t for t in cleaned.split() if t]


def _titlecase(token: str) -> str:
    """Title case that survives hyphens, so "barrott-jones" keeps both halves."""
    return "-".join(part.capitalize() for part in token.split("-"))


def normalise(name: str | None) -> str | None:
    """A referee's join key: one initial, then the surname. None for nothing.

    A middle name is dropped rather than kept as a second initial, because
    football-data writes exactly one and the key has to match theirs. Particles
    are part of the surname: "Robert Van Der Berg" is "R Van Der Berg", not
    "R Berg", since dropping them would merge distinct officials.
    """
    if not name or not name.strip():
        return None
    if name in CROSSWALK:
        return CROSSWALK[name]

    tokens = _tokens(name)
    if not tokens:
        return None
    if len(tokens) == 1:
        return _titlecase(tokens[0])

    first, rest = tokens[0], tokens[1:]
    # Drop a middle name or middle initial, so the key carries one initial like
    # football-data's does. A particle is never a middle name: it opens the
    # surname and stays attached to it.
    if len(rest) > 1 and rest[0].lower() not in _PARTICLES:
        rest = rest[1:]

    surname = " ".join(_titlecase(t) for t in rest)
    return f"{first[0].upper()} {surname}"


def same(left: str | None, right: str | None) -> bool:
    """Do two spellings refer to one official?"""
    a, b = normalise(left), normalise(right)
    return a is not None and a == b


def display(name: str | None) -> str | None:
    """The spelling to print. The country suffix goes, everything else stays."""
    if not name or not name.strip():
        return None
    return " ".join(_tokens(name))
