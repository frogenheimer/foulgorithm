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


# The twenty-four Championship clubs, in football-data.co.uk's E1 spellings.
#
# These exist for the cups and for nothing else. **No player-level foul data
# exists for any of them**: the worldfootballR archive is first tier only for
# England, FPL is the Premier League by definition, and the league's own API
# does not know the second tier exists. See features/promotion.py, which
# measured the consequence: a promoted club's Championship rate used raw scores
# 16% worse than the league mean.
#
# So these clubs get team-level football-data numbers and match totals. They
# never get a player pick, and has_player_data() below is what enforces that.
CHAMPIONSHIP_CLUBS = frozenset({
    "Birmingham",
    "Blackburn",
    "Bolton",
    "Bristol City",
    "Burnley",
    "Cardiff",
    "Charlton",
    "Derby",
    "Lincoln",
    "Middlesbrough",
    "Millwall",
    "Norwich",
    "Portsmouth",
    "Preston",
    "QPR",
    "Sheffield United",
    "Southampton",
    "Stoke",
    "Swansea",
    "Watford",
    "West Brom",
    "West Ham",
    "Wolves",
    "Wrexham",
})

PREMIER_LEAGUE_CLUBS = frozenset(FIXTURE_TO_FPL)

PREMIER, CHAMPIONSHIP = "E0", "E1"


def division_of(fixture_team: str) -> str | None:
    """The football-data division file this club's matches live in, or None.

    None is the ordinary answer for most of a cup draw. League One, League Two
    and non-league clubs are not errors, they are simply clubs we hold nothing
    for, and the cup publisher drops their ties rather than raising.
    """
    if fixture_team in PREMIER_LEAGUE_CLUBS:
        return PREMIER
    if fixture_team in CHAMPIONSHIP_CLUBS:
        return CHAMPIONSHIP
    return None


def holds_data(fixture_team: str) -> bool:
    """Do we hold match history for this club at all?"""
    return division_of(fixture_team) is not None


def has_player_data(fixture_team: str) -> bool:
    """Can we publish a PLAYER-level number for this club?

    Only the top flight. Kept separate from holds_data() on purpose: a
    Championship club has a full team record and no player rows whatsoever, and
    conflating the two is how a positional prior gets published looking like a
    prediction about a person.
    """
    return division_of(fixture_team) == PREMIER


# API-Football's spellings for the Championship, where they differ from
# football-data's. Written down rather than fuzzy-matched, for the same reason
# the other three maps are: an unknown club should be visible in a diff.
API_FOOTBALL_TO_FIXTURE = {
    "Birmingham City": "Birmingham",
    "Blackburn Rovers": "Blackburn",
    "Bolton Wanderers": "Bolton",
    "Bristol City": "Bristol City",
    "Burnley": "Burnley",
    "Cardiff City": "Cardiff",
    "Charlton Athletic": "Charlton",
    "Derby County": "Derby",
    "Lincoln City": "Lincoln",
    "Middlesbrough": "Middlesbrough",
    "Millwall": "Millwall",
    "Norwich City": "Norwich",
    "Portsmouth": "Portsmouth",
    "Preston North End": "Preston",
    "Preston": "Preston",
    "Queens Park Rangers": "QPR",
    "Sheffield Wednesday": "Sheffield Weds",
    "Sheffield Weds": "Sheffield Weds",
    "Sheffield Utd": "Sheffield United",
    "Southampton": "Southampton",
    "Stoke City": "Stoke",
    "Swansea City": "Swansea",
    "Watford": "Watford",
    "West Bromwich Albion": "West Brom",
    "West Brom": "West Brom",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    "Wrexham": "Wrexham",
}


def to_fixture_name(name: str) -> str | None:
    """Any source's club spelling to the fixture-source name, or None.

    API-Football spells the same twenty clubs a fourth way, mostly matching
    either the league API's full names or the fixture source's short ones.
    None, never a guess: the caller decides whether an unknown club is an
    error (our own cup tie failing to match) or just another team in the
    competition. Salford are not a problem, they are a third-round draw: we
    hold nothing for them and their tie is dropped rather than half-rendered.
    """
    if name in FIXTURE_TO_FPL or name in CHAMPIONSHIP_CLUBS:
        return name
    if name in PULSELIVE_TO_FIXTURE:
        return PULSELIVE_TO_FIXTURE[name]
    fpl = {v: k for k, v in FIXTURE_TO_FPL.items()}
    if name in fpl:
        return fpl[name]
    mapped = API_FOOTBALL_TO_FIXTURE.get(name)
    if mapped is not None:
        return mapped
    # Championship clubs reach the history map too, and it is the same
    # long-form-to-short translation, so reuse it rather than repeat it.
    mapped = HISTORY_TO_FIXTURE.get(name)
    if mapped in CHAMPIONSHIP_CLUBS or mapped in FIXTURE_TO_FPL:
        return mapped
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
