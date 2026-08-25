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


# Premier League API name -> football-data.co.uk name. A third spelling of the
# same twenty clubs, because every source names them differently.
PULSELIVE_TO_FIXTURE = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton & Hove Albion": "Brighton",
    "Chelsea": "Chelsea",
    "Coventry City": "Coventry",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Hull City": "Hull",
    "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds",
    "Liverpool": "Liverpool",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Sunderland": "Sunderland",
    "Tottenham Hotspur": "Tottenham",
}


def to_fixture_name(name: str) -> str | None:
    """Any source's club spelling to the fixture-source name, or None.

    API-Football spells the same twenty clubs a fourth way, mostly matching
    either the league API's full names or the fixture source's short ones.
    None, never a guess: the caller decides whether an unknown club is an
    error (our own cup tie failing to match) or just another team in the
    competition (Wrexham are not a problem, they are a third-round draw).
    """
    if name in FIXTURE_TO_FPL:
        return name
    if name in PULSELIVE_TO_FIXTURE:
        return PULSELIVE_TO_FIXTURE[name]
    fpl = {v: k for k, v in FIXTURE_TO_FPL.items()}
    if name in fpl:
        return fpl[name]
    return None


def from_pulselive(name: str) -> str:
    if name not in PULSELIVE_TO_FIXTURE:
        raise SourceError(
            f"no fixture club mapped for Premier League API name {name!r}. Add it "
            "to src/foulgorithm/identity/teams.py."
        )
    return PULSELIVE_TO_FIXTURE[name]


# Foul-history club name -> football-data club name. A fourth spelling of the
# same clubs. History says "Brighton & Hove Albion", fixtures say "Brighton",
# and the join silently found nothing, which is how team comparison rows came
# back empty without complaint.
HISTORY_TO_FIXTURE = {
    "Brighton & Hove Albion": "Brighton",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Norwich City": "Norwich",
    "Ipswich Town": "Ipswich",
    "Hull City": "Hull",
    "Coventry City": "Coventry",
    "Cardiff City": "Cardiff",
    "Stoke City": "Stoke",
    "Swansea City": "Swansea",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield United": "Sheffield United",
    "Luton Town": "Luton",
    "Huddersfield Town": "Huddersfield",
}

FIXTURE_TO_HISTORY = {v: k for k, v in HISTORY_TO_FIXTURE.items()}


def history_name(fixture_team: str) -> str:
    """The club as the foul history spells it. Identity when they agree."""
    return FIXTURE_TO_HISTORY.get(fixture_team, fixture_team)


def to_fpl(fixture_team: str) -> str:
    if fixture_team not in FIXTURE_TO_FPL:
        raise SourceError(
            f"no FPL club mapped for {fixture_team!r}. Add it to "
            "src/foulgorithm/identity/teams.py rather than letting it resolve "
            "to an empty squad."
        )
    return FIXTURE_TO_FPL[fixture_team]
