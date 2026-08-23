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

import math
from dataclasses import dataclass

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


def best_combination(legs: list[Leg], target: int) -> tuple[float, tuple[Leg, ...]] | None:
    """The likeliest set of legs hitting `target` fouls exactly, one per player.

    Exact, not a heuristic. The previous version enumerated every combination of
    every size and discarded the ones that missed the target or reused a player,
    which for fourteen players at three lines each is C(42, 4) per target per
    fixture. A publish run spent sixty-five seconds there and evaluated one
    generator 173 million times.

    Choosing at most one leg per player to reach an exact total while maximising
    a product of probabilities is a knapsack. The state is (fouls so far, legs
    so far) and the value is the best log-probability reaching it, so the work is
    players x target x legs-per-player instead of combinatorial.

    Log probabilities rather than products: forty multiplications of numbers
    around 0.1 underflow, and comparing sums avoids it entirely.

    `tests/test_combinations_speed.py` checks this against the exhaustive search
    it replaced, on random pools, because "faster" is only worth having if the
    answer is the same.
    """
    if not legs or target <= 0:
        return None

    by_player: dict[str, list[Leg]] = {}
    for leg in legs:
        by_player.setdefault(leg.player, []).append(leg)

    # (fouls, legs used) -> (total log prob, chosen legs)
    best: dict[tuple[int, int], tuple[float, tuple[Leg, ...]]] = {(0, 0): (0.0, ())}

    for options in by_player.values():
        nxt = dict(best)
        for (fouls, used), (score, chosen) in best.items():
            if used >= MAX_LEGS:
                continue
            for leg in options:
                total = fouls + leg.fouls
                if total > target or leg.prob <= 0:
                    continue
                key = (total, used + 1)
                candidate = score + math.log(leg.prob)
                held = nxt.get(key)
                if held is None or candidate > held[0]:
                    nxt[key] = (candidate, chosen + (leg,))
        best = nxt

    winner = None
    for (fouls, used), (score, chosen) in best.items():
        if fouls != target or not (MIN_LEGS <= used <= MAX_LEGS):
            continue
        if winner is None or score > winner[0]:
            winner = (score, chosen)

    if winner is None:
        return None
    return math.exp(winner[0]), winner[1]


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
        found = best_combination(legs, target)
        if not found:
            continue
        p, chosen = found
        tickets.append(
            Ticket(
                target=target,
                legs=list(chosen),
                probability=p,
                fair=round(1 / p, 2) if p > 0 else float("inf"),
            )
        )
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
