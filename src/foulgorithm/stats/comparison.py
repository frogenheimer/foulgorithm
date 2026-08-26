"""Two team records, mirrored into the rows a cup page renders.

The shape is the league fixture page's head-to-head, and it is the right one:
one row with a shared centre label means the comparison happens by looking
across, rather than by holding a number in your head while you hunt for its
opposite in a second table.

What is different here is that the two sides can be in different divisions. So
every value carries its OWN division's average and its OWN division's rank, and
neither number is ever adjusted toward the other. Adjusting would be a model
judgement inside a section that has none, and it would hide the very thing the
reader needs to see, which is that these are two different scales.
"""

from __future__ import annotations

from foulgorithm.stats import league_baseline as lb
from foulgorithm.stats.team_record import DIVISION_NAMES, TeamRecord

#: (block title, [(record attribute, baseline key, row label)]). Fouls first:
#: it is what the site is about and what a reader came for.
BLOCKS = (
    ("Fouls", (
        ("fouls_per_match", "foulsPerMatch", "Fouls committed per match"),
        ("fouls_won_per_match", "foulsWonPerMatch", "Fouls won per match"),
        ("fouls_home", "foulsPerMatch", "Fouls committed at home"),
        ("fouls_away", "foulsPerMatch", "Fouls committed away"),
        ("cards_per_foul", "cardsPerFoul", "Cards per foul"),
    )),
    ("Cards", (
        ("yellows_per_match", "yellowsPerMatch", "Yellow cards per match"),
        ("cards_per_match", None, "Cards per match"),
        ("reds_per_match", "redsPerMatch", "Red cards per match"),
    )),
    ("Match shape", (
        ("shots_per_match", "shotsPerMatch", "Shots per match"),
        ("shots_on_target_per_match", "shotsOnTargetPerMatch", "Shots on target per match"),
        ("corners_per_match", "cornersPerMatch", "Corners per match"),
        ("goals_for_per_match", "goalsForPerMatch", "Goals scored per match"),
        ("goals_against_per_match", "goalsAgainstPerMatch", "Goals conceded per match"),
    )),
)


def build(
    home: TeamRecord,
    away: TeamRecord,
    baselines: dict[str, dict],
    rates: dict[str, dict[str, float]],
) -> list[dict]:
    """The comparison blocks.

    `baselines` and `rates` are keyed by division: each side is measured
    against the league it plays in, never against a pooled one.
    """
    out = []
    for title, fields in BLOCKS:
        rows = [
            _row(home, away, attr, key, label, baselines, rates)
            for attr, key, label in fields
        ]
        rows = [r for r in rows if r["home"] is not None or r["away"] is not None]
        if rows:
            out.append({"title": title, "rows": rows})
    return out


def _row(home, away, attr, key, label, baselines, rates):
    h, a = getattr(home, attr), getattr(away, attr)

    def context(record, value):
        division = record.division
        if value is None or division is None:
            return None, None
        note = lb.marker(value, baselines.get(division, {}), key, division) if key else None
        rank = lb.rank_label(
            lb.rank(value, _rates_for(rates, division, attr)), division
        )
        return note, rank

    home_note, home_rank = context(home, h)
    away_note, away_rank = context(away, a)

    return {
        "label": label,
        "home": h,
        "away": a,
        "higher": None if h is None or a is None else ("home" if h > a else "away"),
        "homeNote": home_note,
        "awayNote": away_note,
        "homeRank": home_rank,
        "awayRank": away_rank,
    }


def _rates_for(rates: dict, division: str, attr: str) -> dict[str, float]:
    """Every club's value for this stat in one division, for the rank."""
    table = rates.get(division) or {}
    # Callers pass either {division: {club: value}} for the headline stat or
    # {division: {attr: {club: value}}} when ranking several. Both are accepted
    # so a page that only ranks fouls does not have to build the rest.
    inner = table.get(attr)
    return inner if isinstance(inner, dict) else table


def cross_division_note(home: TeamRecord, away: TeamRecord) -> str | None:
    """One line, when the two sides are not measured on the same scale.

    The divisions barely differ in LEVEL, which is exactly why this warning is
    needed: 10.75 against 10.81 over the published window invites the reader to
    treat the numbers as interchangeable. They are not. The Championship spread
    is about 40% wider, so the same distance from average means a different
    thing in each league, and only about 37% of a second-tier club's
    distinctiveness carries into the top flight at all.
    """
    hd, ad = home.division, away.division
    if hd is None or ad is None or hd == ad:
        return None
    return (
        f"{home.team} play in the {DIVISION_NAMES.get(hd, hd)} and {away.team} in the "
        f"{DIVISION_NAMES.get(ad, ad)}, so these columns are two different scales. "
        "The two divisions average almost the same fouls per match, but second-tier "
        "rates are spread far wider, and only about 37% of a club's distance from "
        "its own division's average carries into the top flight. Read each side "
        "against its own league, not against the other."
    )
