"""Buildable tickets: a set of players whose fouls sum to a target total.

Closer to how people actually bet than a list of independent probabilities. For
a target of 6 fouls in a match, find the combination most likely to land, which
might be three players at 2+ each, or 3+2+1 across three, or two players at 3+.

⚠️ The honest caveat, and it is not small. Combining probabilities by
multiplying assumes the legs are independent. They are not. Two players in the
same match share a referee, a game state and a tempo, so if one is fouling
freely the other probably is too. That correlation is POSITIVE, which means
multiplying UNDERSTATES the true chance of the combination landing.

So these numbers are a floor rather than an estimate, and the site must say so.
Modelling the correlation properly needs a joint model over players in a match,
which is a real piece of work and is not this.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

# Legs per ticket. Two is thin, four is already a long shot at these prices.
MIN_LEGS = 2
MAX_LEGS = 4
# How many players per fixture to search over. The search is combinatorial, so
# this is the knob that keeps it fast.
SEARCH_WIDTH = 14


@dataclass(frozen=True)
class Leg:
    player: str
    team: str
    market: str
    line: float
    prob: float

    @property
    def fouls(self) -> int:
        """The whole number this leg contributes to the target."""
        return int(self.line + 0.5)


@dataclass(frozen=True)
class Ticket:
    target: int
    legs: list[Leg]
    probability: float
    fair: float

    @property
    def shape(self) -> str:
        """Human shorthand, e.g. "2+2+2"."""
        return "+".join(str(leg.fouls) for leg in sorted(self.legs, key=lambda x: -x.fouls))


def _legs_for(players: list[dict], market: str) -> list[Leg]:
    out = []
    for row in players[:SEARCH_WIDTH]:
        block = row[market]
        for n in (1, 2, 3):
            p = block[f"p{n}plus"]
            if p < 0.10:
                continue
            out.append(
                Leg(
                    player=row["player"],
                    team=row["team"],
                    market=market,
                    line=n - 0.5,
                    prob=p,
                )
            )
    return out


def best_tickets(
    fixture: dict,
    market: str = "committed",
    targets: tuple[int, ...] = (4, 5, 6),
) -> list[Ticket]:
    """The likeliest combination reaching each target total."""
    legs: list[Leg] = []
    for players in fixture["teams"].values():
        legs.extend(_legs_for(players, market))

    # Keep one line per player per search: mixing 1+ and 2+ for the same player
    # would double-count him, since 2+ already implies 1+.
    tickets = []
    for target in targets:
        best: Ticket | None = None
        for size in range(MIN_LEGS, MAX_LEGS + 1):
            for combo in combinations(legs, size):
                if len({leg.player for leg in combo}) != size:
                    continue
                if sum(leg.fouls for leg in combo) != target:
                    continue
                p = 1.0
                for leg in combo:
                    p *= leg.prob
                if best is None or p > best.probability:
                    best = Ticket(
                        target=target,
                        legs=list(combo),
                        probability=p,
                        fair=round(1 / p, 2) if p > 0 else float("inf"),
                    )
        if best:
            tickets.append(best)
    return tickets


def serialise(ticket: Ticket) -> dict:
    return {
        "target": ticket.target,
        "shape": ticket.shape,
        "probability": round(ticket.probability, 4),
        "outOf100": round(ticket.probability * 100),
        "fair": ticket.fair,
        "legs": [
            {
                "player": leg.player,
                "team": leg.team,
                "line": leg.line,
                "fouls": leg.fouls,
                "prob": round(leg.prob, 4),
                "market": leg.market,
            }
            for leg in sorted(ticket.legs, key=lambda x: -x.fouls)
        ],
    }
