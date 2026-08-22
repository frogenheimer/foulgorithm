"""Map club names between sources.

football-data.co.uk says "Man United", FPL says "Man Utd". Neither is wrong and
neither will change for us, so the mapping is written down once, here, and
checked in a diff rather than guessed at runtime.

Deliberately exhaustive and deliberately strict: an unknown club raises rather
than silently producing an empty squad, because an empty squad looks like a
fixture with no players rather than like a bug.
"""

from __future__ import annotations

from foulgorithm.sources.base import SourceError

# football-data.co.uk name -> FPL name
FIXTURE_TO_FPL = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton": "Brighton",
    "Chelsea": "Chelsea",
    "Coventry": "Coventry City",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Hull": "Hull City",
    "Ipswich": "Ipswich Town",
    "Leeds": "Leeds",
    "Liverpool": "Liverpool",
    "Man City": "Man City",
    "Man United": "Man Utd",
    "Newcastle": "Newcastle",
    "Nott'm Forest": "Nott'm Forest",
    "Tottenham": "Spurs",
    "Sunderland": "Sunderland",
}


def to_fpl(fixture_team: str) -> str:
    if fixture_team not in FIXTURE_TO_FPL:
        raise SourceError(
            f"no FPL club mapped for {fixture_team!r}. Add it to "
            "src/foulgorithm/identity/teams.py rather than letting it resolve "
            "to an empty squad."
        )
    return FIXTURE_TO_FPL[fixture_team]
