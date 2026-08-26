"""Team foul priors for newly promoted clubs.

A promoted club arrives with no Premier League history at all, so it gets the
league mean, which is a guess wearing a number's clothes. That stopped being
hypothetical when Coventry and Hull came up for 2026/27.

**Championship PLAYER data was thought not to exist, and it does.** This module
was written on the belief that FBref's top-five-leagues coverage was the only
route to per-player fouls, so the second tier was unreachable. On 26 August 2026
the Premier League's own API turned out to carry ranked player stats for
competition 12 as well as competition 1: fouls, fouls won, tackles, cards,
appearances and minutes, for 681 Championship players. See
`sources/player_stats.py`.

**That does not retire this module.** What the league publishes is SEASON
TOTALS, not per-match rows, so it gives a rate to display and not the per-match
variance a model trains on. The team-level transfer measured below is still the
honest bridge for a promoted club, and `models/cup_totals` still depends on it.
What changed is that a page may now show a Championship player's rate, which it
could not before.

The transfer is measured rather than assumed. Every club promoted since 2001
has a final Championship season and a first Premier League season, which is a
natural experiment with 66 observations.

**The obvious version of this makes things worse.** Taking a promoted club's
Championship fouls per match at face value scores 16% WORSE than simply using
the league average, despite the two correlating at +0.63. The mean ratio between
the two divisions is 0.990, so close to one that it invites exactly that mistake.

The ratio is a red herring. Championship foul rates are spread far wider than
Premier League ones, so a club 3 fouls above its division average does not
arrive 3 fouls above the Premier League average. Only about 37% of the deviation
carries. Shrunk by that factor, the Championship rate beats the league mean by
7.7% on leave-one-out error. Used raw, it loses.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from functools import lru_cache

from foulgorithm.sources import football_data

FIRST_SEASON = 2001
PREMIER, CHAMPIONSHIP = "E0", "E1"


@dataclass(frozen=True)
class Discount:
    """How a promoted club's fouls carry into the Premier League.

    `beta` is the number that matters and `ratio` is the one that misleads. See
    the module docstring: the ratio is essentially 1.0, which suggests the rate
    transfers untouched, and it does not.
    """

    beta: float           # fraction of a club's Championship deviation that carries
    ratio: float          # mean level ratio, kept because it is worth showing as a trap
    spread: float
    observations: int

    def describe(self) -> str:
        return (
            f"beta {self.beta:.3f}, level ratio {self.ratio:.3f} +/- {self.spread:.3f}, "
            f"over {self.observations} promoted clubs"
        )


def _labels(first: int = FIRST_SEASON) -> list[str]:
    from foulgorithm.publish.site_export import season_labels

    return season_labels(first)


COMMITTED, DRAWN = "committed", "drawn"


@lru_cache(maxsize=128)
def _totals(season: str, division: str, kind: str = COMMITTED) -> dict[str, list[int]]:
    """Per-club foul counts per match.

    `committed` is the club's own fouls. `drawn` is its opponents' fouls, which
    is what an opponent factor actually needs and is not the same quantity: a
    side that fouls a lot need not be one that gets fouled a lot.
    """
    try:
        rows = football_data.parse(football_data.fetch(season, division=division))
    except Exception:
        return {}

    totals: dict[str, list[int]] = {}
    for r in rows:
        for side, other in (("home", "away"), ("away", "home")):
            team = r[f"{side}_team_raw"]
            fouls = r[f"{side if kind == COMMITTED else other}_fouls"]
            if team and fouls is not None:
                totals.setdefault(team, []).append(fouls)
    return totals


def _teams_in(season: str, division: str) -> set[str]:
    """Membership only. One appearance is enough to place a club in a division.

    Kept separate from the rate because they need different thresholds. In
    August a promoted club has played once, which settles which division it is
    in and says nothing about how it fouls.
    """
    return set(_totals(season, division))


def _team_fouls(season: str, division: str, kind: str = COMMITTED) -> dict[str, float]:
    """Fouls per match per club, both venues pooled. Needs a real sample."""
    return {
        t: statistics.fmean(v)
        for t, v in _totals(season, division, kind).items()
        if len(v) >= 10
    }


def _previous(season: str) -> str:
    start = int(season.split("-")[0]) - 1
    return f"{start}-{(start + 1) % 100:02d}"


def current_season() -> str:
    """The season now being played, derived from the calendar.

    A season starting in August of year Y is labelled Y-(Y+1). Never hard-coded:
    the 2025 version needed editing every August to survive.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    start = now.year if now.month >= 8 else now.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _live_premier_teams() -> set[str]:
    """This season's Premier League clubs, from the league's own fixture list.

    football-data.co.uk does not publish a season's file until it is underway,
    so in August the historical route returns nothing precisely when a promoted
    club most needs a prior. The fixture list knows immediately.

    Names come back in fixture spelling, which is what football-data.co.uk uses
    in its own files ("Man City", not "Manchester City"), so no further mapping
    is needed. Mapping to the player-history spelling here was a real bug: it
    turned "Coventry" into "Coventry City" and then matched nothing.
    """
    try:
        from foulgorithm.identity.teams import from_pulselive
        from foulgorithm.sources import pulselive

        return {from_pulselive(raw) for f in pulselive.fixtures() for raw in (f.home, f.away)}
    except Exception:
        return set()


def promoted_clubs(season: str) -> list[str]:
    """Clubs in the Premier League this season that were not in it last season.

    Derived, never hard-coded. The 2025 version listed 20 club names in a config
    file and needed editing every August to survive.
    """
    before = _teams_in(_previous(season), PREMIER)
    if not before:
        return []
    now = _teams_in(season, PREMIER) or _live_premier_teams()
    if not now:
        return []
    # A club we cannot place in the second tier either is not a promotion we can
    # act on, so it is left out rather than reported as one and then dropped.
    second = _teams_in(_previous(season), CHAMPIONSHIP)
    return sorted((now - before) & second)


@lru_cache(maxsize=4)
def tier_discount(kind: str = COMMITTED) -> Discount:
    """Measured across every promotion since 2001.

    Regresses a club's first Premier League deviation on its final Championship
    deviation, both taken from their own division's average that season. The
    slope is how much of a club's distinctiveness survives promotion.

    Clubs are matched by name within football-data.co.uk, which spells them
    consistently across its own divisions, so no crosswalk is needed here.
    """
    devs: list[tuple[float, float]] = []
    ratios: list[float] = []
    for season in _labels()[1:]:
        top = _team_fouls(season, PREMIER, kind)
        second = _team_fouls(_previous(season), CHAMPIONSHIP, kind)
        if not top or not second:
            continue
        cmean, pmean = statistics.fmean(second.values()), statistics.fmean(top.values())
        for club in promoted_clubs(season):
            if club in second and club in top and second[club] > 0:
                devs.append((second[club] - cmean, top[club] - pmean))
                ratios.append(top[club] / second[club])

    if len(devs) < 20:
        # Never silently fall back to 1.0. A missing measurement is not
        # "no effect", and a beta of 1.0 is precisely the wrong default here.
        raise RuntimeError(f"only {len(devs)} promotions measurable, refusing to guess")

    xb = statistics.fmean(x for x, _ in devs)
    yb = statistics.fmean(y for _, y in devs)
    den = sum((x - xb) ** 2 for x, _ in devs)
    beta = sum((x - xb) * (y - yb) for x, y in devs) / den if den else 0.0
    return Discount(
        beta=beta,
        ratio=statistics.fmean(ratios),
        spread=statistics.stdev(ratios),
        observations=len(devs),
    )


@lru_cache(maxsize=8)
def league_mean(season: str | None = None, kind: str = COMMITTED) -> float:
    """Premier League fouls per club per match, most recent settled season."""
    season = season or _labels()[-1]
    values = list(_team_fouls(season, PREMIER, kind).values())
    if not values:
        values = list(_team_fouls(_previous(season), PREMIER, kind).values())
    return statistics.fmean(values) if values else 10.5


def team_prior(club: str, season: str, kind: str = COMMITTED) -> float | None:
    """Expected fouls per match for a promoted club, or None if not applicable.

    Returns None for an established club, which has its own history and needs no
    help, and None for a club with no Championship record either, which we
    simply cannot inform. The caller falls back to the league mean.

    None is deliberate rather than an exception. An unresolved IDENTITY halts the
    pipeline, per docs/04-identity-resolution.md, because guessing there
    transplants one player's history onto another. A missing second-tier season
    is a different thing: we know exactly who the club is and have nothing to say
    about it.
    """
    if club not in promoted_clubs(season):
        return None
    second = _team_fouls(_previous(season), CHAMPIONSHIP, kind)
    if club not in second:
        return None
    # Shrink the club's deviation, do not carry its level. Carrying the level is
    # the version that loses to a plain league average.
    deviation = second[club] - statistics.fmean(second.values())
    return league_mean(season, kind) + tier_discount(kind).beta * deviation


def second_tier_prior(
    club: str, season: str | None = None, kind: str = COMMITTED
) -> float | None:
    """A Championship club's expected fouls on the PREMIER LEAGUE scale.

    `team_prior` answers this for a club that has just gone up. A cup tie needs
    the same answer for one that has not: Wrexham are still in the Championship
    and are about to play Arsenal, and the tie needs a number for them.

    Same inference, same fitted beta, one gate removed. The rule that must not
    break is the one this module exists for: **the club's level does not
    travel, only its shrunk deviation does.** The two divisions' means differ by
    almost nothing, which is exactly what makes carrying the raw rate tempting,
    and carrying it scores 16% worse than using the league average.

    None for a club with no measurable second-tier season. The caller falls
    back to the league mean and says so, rather than inventing one.
    """
    season = season or current_season()
    # The club's most recent Championship season with a real sample. This
    # season first: a club three games in has no rate yet and the one before
    # is the honest answer, not a reason to give up.
    for label in (season, _previous(season)):
        rates = _team_fouls(label, CHAMPIONSHIP, kind)
        if club in rates:
            deviation = rates[club] - statistics.fmean(rates.values())
            return league_mean(season, kind) + tier_discount(kind).beta * deviation
    return None


def opponent_factor(club: str, season: str) -> float | None:
    """How many fouls a promoted club draws, relative to the league average.

    Returns None for anyone we cannot inform, and the caller keeps its own
    behaviour. This exists because `opponent_factor` in the player model
    silently returns 1.0 below 200 rows of history, and a promoted club has
    zero. Silently average is the failure this project is meant not to make.
    """
    prior = team_prior(club, season, DRAWN)
    if prior is None:
        return None
    return prior / max(league_mean(season, DRAWN), 1e-6)


if __name__ == "__main__":
    for kind in (COMMITTED, DRAWN):
        print(f"{kind:<12}{tier_discount(kind).describe()}")
        print(f"{'':12}league mean {league_mean(kind=kind):.2f} per club per match")
    print()
    for season in _labels()[-3:]:
        clubs = promoted_clubs(season)
        if not clubs:
            continue
        print(season)
        for club in clubs:
            prior = team_prior(club, season)
            factor = opponent_factor(club, season)
            print(
                f"  {club:<14}commits {prior:5.2f}   draws x{factor:.3f}"
                if prior and factor
                else f"  {club:<14}no second-tier record"
            )
