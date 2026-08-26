"""The appointed official's record, published as an observation.

Carried from publish/site_export, and worth repeating because it is the whole
caveat: **a referee's fouls per match is not a referee effect.** One handed
more derbies shows more of everything without being any stricter, and
separating the two needs a model with team effects in it. Nothing here is that
model, and nothing here reaches one.

`cards_per_foul` is the column worth reading. Cards per match rises with how
physical the game was; cards per foul asks how likely he is to book an offence
he has already given, which is much closer to what people mean by strict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from foulgorithm.identity import referees

#: Below this many matches the record is shown WITH its count and flagged,
#: never hidden. A reader who can see "4 matches" discounts it himself.
THIN_MATCHES = 20


@dataclass(frozen=True)
class ClubUnder:
    """One club's record with this official in charge."""

    club: str
    matches: int
    fouls_per_match: float | None = None
    yellows_per_match: float | None = None


@dataclass(frozen=True)
class RefereeRecord:
    referee: str
    key: str
    matches: int
    fouls_per_match: float | None = None
    cards_per_match: float | None = None
    cards_per_foul: float | None = None
    _by_club: dict[str, ClubUnder] = field(default_factory=dict, repr=False)

    @property
    def thin(self) -> bool:
        return self.matches < THIN_MATCHES

    def club(self, name: str) -> ClubUnder:
        return self._by_club.get(name, ClubUnder(club=name, matches=0))


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def build(referee: str | None, matches: list[dict]) -> RefereeRecord | None:
    """The official's record across whatever history is passed in.

    `referee` may arrive in any source's spelling. The join runs on the
    normalised key, which is what fixed a cup slate carrying "Andrew Kitchen"
    against a history that writes "A Kitchen" and silently matching nothing.
    """
    key = referees.normalise(referee)
    if key is None:
        return None

    his = [m for m in matches if referees.normalise(m.get("referee_raw")) == key]
    totals = [m["home_fouls"] + m["away_fouls"] for m in his]

    carded = [
        m for m in his
        if m.get("home_yellows") is not None and m.get("away_yellows") is not None
    ]
    cards = [
        (m["home_yellows"] or 0) + (m["away_yellows"] or 0)
        + (m.get("home_reds") or 0) + (m.get("away_reds") or 0)
        for m in carded
    ]
    carded_fouls = sum(m["home_fouls"] + m["away_fouls"] for m in carded)

    return RefereeRecord(
        referee=referees.display(referee),
        key=key,
        matches=len(his),
        fouls_per_match=_mean(totals),
        cards_per_match=_mean(cards),
        cards_per_foul=round(sum(cards) / carded_fouls, 4) if carded_fouls else None,
        _by_club=_by_club(his),
    )


def _by_club(matches: list[dict]) -> dict[str, ClubUnder]:
    fouls: dict[str, list[int]] = {}
    yellows: dict[str, list[int]] = {}
    for m in matches:
        for side in ("home", "away"):
            club = m[f"{side}_team_raw"]
            fouls.setdefault(club, []).append(m[f"{side}_fouls"])
            if m.get(f"{side}_yellows") is not None:
                yellows.setdefault(club, []).append(m[f"{side}_yellows"])
    return {
        club: ClubUnder(
            club=club,
            matches=len(values),
            fouls_per_match=_mean(values),
            yellows_per_match=_mean(yellows.get(club, [])),
        )
        for club, values in fouls.items()
    }
