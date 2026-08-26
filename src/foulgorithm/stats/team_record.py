"""One club's raw record, from football-data.co.uk, in either division.

The cup pages set a Premier League club against a Championship one. That is
only honest if both sides are measured the same way by the same source, so
everything here comes from the E0 and E1 CSVs and nothing here reaches for the
Premier League's richer player feeds. A comparison built half from API-Football
player rows and half from a CSV would not be a comparison.

Two rules the numbers obey.

**A club that changed division keeps its spells apart.** Burnley's 2025-26 was
the Championship and their 2026-27 is the Premier League. The pooled rate is
published, because a bigger sample is worth having, but `spell_label()` says
where the matches came from so nobody reads one number as one league.

**An absent column is absent, never zero.** Season files before 2000-01 carry
results without cards, and counting those as zero yellows reads as "never
booked anyone", which is a claim rather than a gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from foulgorithm.identity.teams import CHAMPIONSHIP, PREMIER

DIVISION_NAMES = {PREMIER: "Premier League", CHAMPIONSHIP: "Championship"}


@dataclass(frozen=True)
class Spell:
    """A run of matches in one season and one division."""

    season: str
    division: str
    matches: int


@dataclass(frozen=True)
class TeamRecord:
    team: str
    matches: int
    spells: tuple[Spell, ...] = ()

    # The foul core.
    fouls_per_match: float | None = None
    fouls_won_per_match: float | None = None
    fouls_home: float | None = None
    fouls_away: float | None = None
    cards_per_foul: float | None = None

    # Cards. `carded_matches` is the denominator for the card figures and is
    # published so a reader can see it is smaller than `matches`.
    yellows_per_match: float | None = None
    cards_per_match: float | None = None
    reds_per_match: float | None = None
    carded_matches: int = 0

    # Match shape.
    shots_per_match: float | None = None
    shots_on_target_per_match: float | None = None
    corners_per_match: float | None = None
    goals_for_per_match: float | None = None
    goals_against_per_match: float | None = None

    @property
    def divisions(self) -> tuple[str, ...]:
        seen: list[str] = []
        for spell in self.spells:
            if spell.division not in seen:
                seen.append(spell.division)
        return tuple(seen)

    @property
    def crossed_divisions(self) -> bool:
        return len(self.divisions) > 1

    @property
    def division(self) -> str | None:
        """The division of the most recent spell: where this club is now."""
        return self.spells[-1].division if self.spells else None

    def spell_label(self) -> str:
        """"38 in the Championship, 8 in the Premier League"."""
        totals: dict[str, int] = {}
        order: list[str] = []
        for spell in self.spells:
            if spell.division not in totals:
                order.append(spell.division)
            totals[spell.division] = totals.get(spell.division, 0) + spell.matches
        parts = [
            f"{totals[d]} in the {DIVISION_NAMES.get(d, d)}" for d in order
        ]
        return ", ".join(parts)


def _mean(values: list[float]) -> float | None:
    """None for an empty list. An average of nothing is not zero."""
    return round(sum(values) / len(values), 2) if values else None


def build(team: str, matches: list[dict]) -> TeamRecord:
    """A club's record from parsed football-data rows.

    Rows are the shape `sources.football_data.parse` returns, with `season` and
    `division` added by the loader. Rows the club did not play in are ignored,
    so a whole division's matches can be passed in without filtering first.
    """
    played = [
        m for m in matches
        if m["home_team_raw"] == team or m["away_team_raw"] == team
    ]
    if not played:
        return TeamRecord(team=team, matches=0)

    def side(m: dict) -> str:
        return "home" if m["home_team_raw"] == team else "away"

    def mine(m: dict, stat: str):
        return m.get(f"{side(m)}_{stat}")

    def theirs(m: dict, stat: str):
        return m.get(f"{'away' if side(m) == 'home' else 'home'}_{stat}")

    fouls = [mine(m, "fouls") for m in played]
    won = [theirs(m, "fouls") for m in played]
    home_fouls = [m["home_fouls"] for m in played if side(m) == "home"]
    away_fouls = [m["away_fouls"] for m in played if side(m) == "away"]

    # Cards are counted only across matches that HAVE a card column. See the
    # module docstring: a blank is not a zero.
    carded = [
        m for m in played
        if mine(m, "yellows") is not None and theirs(m, "yellows") is not None
    ]
    yellows = [mine(m, "yellows") for m in carded]
    reds = [mine(m, "reds") or 0 for m in carded]
    cards = [y + r for y, r in zip(yellows, reds)]
    carded_fouls = sum(mine(m, "fouls") for m in carded)

    def shape(stat: str, source=mine) -> float | None:
        values = [source(m, stat) for m in played]
        present = [v for v in values if v is not None]
        return _mean(present)

    return TeamRecord(
        team=team,
        matches=len(played),
        spells=_spells(played),
        fouls_per_match=_mean(fouls),
        fouls_won_per_match=_mean(won),
        fouls_home=_mean(home_fouls),
        fouls_away=_mean(away_fouls),
        cards_per_foul=round(sum(cards) / carded_fouls, 4) if carded_fouls else None,
        yellows_per_match=_mean(yellows),
        cards_per_match=_mean(cards),
        reds_per_match=_mean(reds),
        carded_matches=len(carded),
        shots_per_match=shape("shots"),
        shots_on_target_per_match=shape("shots_on_target"),
        corners_per_match=shape("corners"),
        goals_for_per_match=shape("goals"),
        goals_against_per_match=shape("goals", source=theirs),
    )


def _spells(played: list[dict]) -> tuple[Spell, ...]:
    """One entry per (season, division) played, oldest first."""
    counts: dict[tuple[str, str], int] = {}
    for m in played:
        key = (m.get("season") or "", m.get("division") or "")
        counts[key] = counts.get(key, 0) + 1
    return tuple(
        Spell(season=season, division=division, matches=n)
        for (season, division), n in sorted(counts.items())
    )
