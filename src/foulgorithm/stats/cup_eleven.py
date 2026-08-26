"""The eleven a cup page shows, predicted before the sheets land.

Deliberately separate from the league's likely-eleven work, for one structural
reason: **cup sides are rotated.** A manager changes eight or nine players for
an early round, so an XI predicted from league minutes is confidently wrong for
exactly the games these pages cover, and wrong in the way that matters, which
is that it looks authoritative.

So the prediction is the simplest thing that is defensible: the busiest
goalkeeper and the ten busiest outfielders. A cleverer model here would buy
nothing except a better disguise for the same guess, and the honest move is the
label rather than the machinery. `note` travels with every predicted eleven and
the page is not allowed to render one without it.

At T-60 the real sheet arrives through `jobs/cup_watch` and `confirm()` takes
over. A confirmed eleven carries no caveat, because it is no longer a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from foulgorithm.sources.player_stats import PlayerStats

#: Said on every predicted eleven, never optional. Cup rotation is the single
#: biggest source of error on these pages and the reader has to be told.
ROTATION_NOTE = (
    "Predicted from league minutes, and cup sides rotate heavily: managers "
    "often change eight or nine players for an early round. Treat this as a "
    "guess at the shape rather than a team sheet. It is replaced by the real "
    "eleven about an hour before kickoff."
)


@dataclass(frozen=True)
class Eleven:
    players: list[PlayerStats]
    confirmed: bool
    note: str | None = None
    #: True when the squad could not field eleven, rather than silently short.
    short: bool = False


def _name_key(name: str) -> tuple[str, ...]:
    """Sorted, normalised tokens, so name order cannot make two of one player.

    Borrowed from publish/player_round, which learned it the hard way: Wataru
    Endo reached a team sheet as "Endo Wataru" and became a second player.
    """
    cleaned = name.lower().replace(".", " ").replace("-", " ")
    return tuple(sorted(t for t in cleaned.split() if t))


def _matches(squad_name: str, sheet_name: str) -> bool:
    """Does this squad member answer to the name on the team sheet?

    Team sheets abbreviate: "M.Sels" for "Matz Sels", "I.Sangare" for "Ibrahim
    Sangare". So a single letter standing in for a full name counts.

    Every token has to be accounted for, and at least one has to be a full word
    matching a full word. Both guards are load-bearing. Without the first,
    "Player 0" matched "Player 1" on the shared word alone. Without the second,
    two sets of initials would resolve to each other, which is how one Danny
    Ward inherits the other's record.
    """
    a, b = _name_key(squad_name), _name_key(sheet_name)
    if a == b:
        return True

    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    remaining = list(long_)
    pairs: list[tuple[str, str]] = []
    for token in short:
        hit = token if token in remaining else None
        if hit is None:
            hit = next(
                (
                    r for r in remaining
                    if (len(token) == 1 and r.startswith(token))
                    or (len(r) == 1 and token.startswith(r))
                ),
                None,
            )
        if hit is None:
            return False
        remaining.remove(hit)
        pairs.append((token, hit))

    return any(len(t) > 1 and t == h for t, h in pairs)


def predict(squad: list[PlayerStats]) -> Eleven:
    """The busiest goalkeeper and the ten busiest outfielders.

    Players with no minutes are never picked: a summer signing with a blank
    record is in the squad and is not evidence of anything, and letting him top
    an XI sorted by name would be worse than leaving him out.
    """
    played = [p for p in squad if p.minutes > 0]
    keepers = sorted((p for p in played if p.position == "G"), key=lambda p: -p.minutes)
    outfield = sorted((p for p in played if p.position != "G"), key=lambda p: -p.minutes)

    chosen = keepers[:1] + outfield[: 11 - len(keepers[:1])]
    return Eleven(
        players=chosen,
        confirmed=False,
        note=ROTATION_NOTE,
        short=len(chosen) < 11,
    )


def confirm(squad: list[PlayerStats], names: list[str]) -> Eleven:
    """The real eleven, in the order the team sheet gave it.

    Order is kept rather than re-sorted: a team sheet runs goalkeeper first and
    that is information. A name we hold no record for still takes its place on
    the pitch with blanks beside it, because a youth debutant is playing
    whether or not we have ever seen him.
    """
    players: list[PlayerStats] = []
    for name in names:
        found = next((p for p in squad if _matches(p.player, name)), None)
        players.append(found or _unknown(name))
    return Eleven(players=players, confirmed=True, note=None, short=len(players) < 11)


def _unknown(name: str) -> PlayerStats:
    """A player on the sheet we hold nothing on. Blanks, never zeroes."""
    return PlayerStats(
        player=name, player_id=-1, club="", position="?", shirt=None,
        appearances=0, minutes=0.0, fouls=0, fouls_won=0, tackles=0,
        yellows=0, reds=0,
        fouls_per_90=None, fouls_won_per_90=None, tackles_per_90=None,
        minutes_by_division={},
    )
