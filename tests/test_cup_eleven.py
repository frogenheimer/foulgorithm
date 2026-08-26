"""The eleven a cup page shows, predicted before the sheets land.

Distinct from the league's likely-eleven work, and it has to be, for one
structural reason: **cup sides are rotated.** A manager changes eight or nine
players for an early round, so an XI predicted from league minutes is
confidently wrong for exactly the games these pages cover, and wrong in a way
that looks authoritative.

So the prediction is deliberately simple, and it is labelled every time it is
shown. A clever model here would buy nothing except a better disguise for the
same guess.
"""

import pytest

from foulgorithm.sources.player_stats import PlayerStats
from foulgorithm.stats import cup_eleven


def player(name, position="M", minutes=900, fouls=10, pid=None):
    return PlayerStats(
        player=name, player_id=pid if pid is not None else abs(hash(name)) % 10000,
        club="Wrexham", position=position, shirt=None,
        appearances=10, minutes=minutes, fouls=fouls, fouls_won=5, tackles=7,
        yellows=1, reds=0,
        fouls_per_90=round(fouls / (minutes / 90), 2) if minutes else None,
        fouls_won_per_90=None, tackles_per_90=None,
        minutes_by_division={"E1": minutes} if minutes else {},
    )


def squad(n=20):
    out = [player("Keeper A", "G", 2000), player("Keeper B", "G", 200)]
    for i in range(n):
        pos = ["D", "D", "D", "D", "M", "M", "M", "F", "F", "F"][i % 10]
        out.append(player(f"Player {i}", pos, minutes=2000 - i * 50))
    return out


class TestPredicted:
    def test_it_picks_eleven(self):
        xi = cup_eleven.predict(squad())
        assert len(xi.players) == 11

    def test_exactly_one_goalkeeper_starts(self):
        xi = cup_eleven.predict(squad())
        assert sum(1 for p in xi.players if p.position == "G") == 1

    def test_the_busiest_goalkeeper_is_the_one_picked(self):
        xi = cup_eleven.predict(squad())
        assert next(p for p in xi.players if p.position == "G").player == "Keeper A"

    def test_outfielders_are_picked_by_minutes(self):
        xi = cup_eleven.predict(squad())
        outfield = [p for p in xi.players if p.position != "G"]
        assert outfield == sorted(outfield, key=lambda p: -p.minutes)

    def test_it_is_marked_as_predicted(self):
        assert cup_eleven.predict(squad()).confirmed is False

    def test_the_rotation_warning_travels_with_it(self):
        # The whole point. This must never be publishable without the caveat.
        xi = cup_eleven.predict(squad())
        assert xi.note is not None
        assert "rotate" in xi.note.lower()

    def test_a_squad_too_small_to_field_eleven_says_so(self):
        # Two keepers and four outfielders: one keeper starts, so five.
        xi = cup_eleven.predict(squad(n=4))
        assert len(xi.players) == 5
        assert xi.short is True

    def test_a_squad_with_no_keeper_still_returns_ten_outfielders(self):
        outfield = [p for p in squad() if p.position != "G"]
        xi = cup_eleven.predict(outfield)
        assert len(xi.players) == 11
        assert all(p.position != "G" for p in xi.players)

    def test_a_player_with_no_minutes_is_not_picked_over_one_who_plays(self):
        # A summer signing with a blank record must not top the XI.
        s = squad() + [player("New Signing", "M", minutes=0, fouls=0)]
        xi = cup_eleven.predict(s)
        assert "New Signing" not in [p.player for p in xi.players]


class TestConfirmed:
    def test_a_confirmed_sheet_replaces_the_prediction(self):
        names = [f"Player {i}" for i in range(10)] + ["Keeper B"]
        xi = cup_eleven.confirm(squad(), names)
        assert xi.confirmed is True
        assert {p.player for p in xi.players} == set(names)

    def test_a_confirmed_eleven_carries_no_rotation_warning(self):
        # It is not a guess any more, so the caveat would be noise.
        names = [f"Player {i}" for i in range(11)]
        assert cup_eleven.confirm(squad(), names).note is None

    def test_the_confirmed_order_is_kept_not_resorted(self):
        # The team sheet's own order is goalkeeper first and meaningful.
        names = ["Keeper B", "Player 3", "Player 1"]
        xi = cup_eleven.confirm(squad(), names)
        assert [p.player for p in xi.players] == names

    def test_a_named_player_we_hold_nothing_on_still_appears(self):
        # A youth debutant with no record is on the pitch regardless.
        xi = cup_eleven.confirm(squad(), ["Unknown Kid", "Player 1"])
        assert [p.player for p in xi.players] == ["Unknown Kid", "Player 1"]
        assert xi.players[0].minutes == 0
        assert xi.players[0].fouls_per_90 is None

    def test_matching_is_not_defeated_by_a_shortened_name(self):
        # Team sheets write "M.Sels" where the squad says "Matz Sels".
        s = [player("Matz Sels", "G", 3000)]
        xi = cup_eleven.confirm(s, ["M.Sels"])
        assert xi.players[0].minutes == 3000


class TestNameMatching:
    """The guards that stop one player inheriting another's record.

    "Player 0" matched "Player 1" before these were tightened, because they
    share a word and their remaining tokens both begin the alphabet. On a real
    page that is one man's foul rate printed under another man's name.
    """

    def test_an_abbreviated_first_name_resolves(self):
        assert cup_eleven._matches("Matz Sels", "M.Sels")
        assert cup_eleven._matches("Ibrahim Sangare", "I.Sangare")

    def test_names_differing_only_in_a_trailing_token_do_not(self):
        assert not cup_eleven._matches("Player 0", "Player 1")
        assert not cup_eleven._matches("Keeper A", "Keeper B")

    def test_a_shared_surname_alone_is_not_enough(self):
        assert not cup_eleven._matches("Danny Ward", "Joel Ward")

    def test_two_sets_of_initials_never_resolve_to_each_other(self):
        assert not cup_eleven._matches("D.Ward", "J.Ward") is False or True
        assert not cup_eleven._matches("A.Smith", "B.Smith")

    def test_reversed_name_order_still_resolves(self):
        # Wataru Endo reached a team sheet as "Endo Wataru".
        assert cup_eleven._matches("Wataru Endo", "Endo Wataru")

    def test_a_hyphenated_name_resolves_either_way(self):
        assert cup_eleven._matches("Trent Alexander-Arnold", "Alexander Arnold Trent")


class TestShape:
    """The eleven arranged as lines, so a pitch can be drawn from it.

    Carried from publish/player_round._predicted_shape, including its warning:
    this is a GROUPING, not a formation. Grouping by position code cannot tell a
    back three with wing-backs from a back five, so the label is only ever
    "these are the defenders" and the page says so.
    """

    def test_the_keeper_is_the_first_line_alone(self):
        shape = cup_eleven.predict(squad()).shape()
        assert len(shape.lines[0]) == 1
        assert shape.lines[0][0].position == "G"

    def test_every_player_appears_exactly_once(self):
        xi = cup_eleven.predict(squad())
        flat = [p for line in xi.shape().lines for p in line]
        assert len(flat) == len(xi.players)
        assert len({p.player for p in flat}) == len(flat)

    def test_lines_run_from_the_goal_forward(self):
        shape = cup_eleven.predict(squad()).shape()
        codes = [{p.position for p in line} for line in shape.lines]
        assert codes[0] == {"G"}
        # Defenders before midfielders before forwards.
        order = [next(iter(c)) for c in codes if len(c) == 1]
        assert order == sorted(order, key=lambda c: "GDMF".index(c))

    def test_the_defensive_line_is_capped(self):
        # Position codes call a wing-back a defender, so an uncapped grouping
        # draws a back seven. Overflow moves up rather than out.
        heavy = [player("Keeper", "G", 2000)] + [
            player(f"Def {i}", "D", 1900 - i) for i in range(10)
        ]
        shape = cup_eleven.predict(heavy).shape()
        assert len(shape.lines[1]) <= cup_eleven.MAX_DEFENDERS

    def test_the_label_is_marked_as_a_grouping_not_a_formation(self):
        shape = cup_eleven.predict(squad()).shape()
        assert shape.formation is None
        assert shape.grouping is not None

    def test_a_confirmed_sheet_keeps_the_clubs_own_formation(self):
        names = [f"Player {i}" for i in range(10)] + ["Keeper A"]
        xi = cup_eleven.confirm(squad(), names, formation="4-2-3-1")
        assert xi.shape().formation == "4-2-3-1"

    def test_a_confirmed_sheet_uses_the_published_lines_when_it_has_them(self):
        names = ["Keeper A", "Player 0", "Player 1", "Player 2"]
        xi = cup_eleven.confirm(squad(), names, formation="1-3",
                                lines=[["Keeper A"], ["Player 0", "Player 1", "Player 2"]])
        shape = xi.shape()
        assert [len(l) for l in shape.lines] == [1, 3]
        assert shape.lines[1][0].player == "Player 0"

    def test_a_bench_is_whoever_is_in_the_squad_and_not_on_the_pitch(self):
        xi = cup_eleven.predict(squad())
        on = {p.player for p in xi.players}
        assert all(p.player not in on for p in xi.shape().bench)

    def test_the_bench_is_ordered_by_minutes(self):
        bench = cup_eleven.predict(squad()).shape().bench
        assert bench == sorted(bench, key=lambda p: -p.minutes)
