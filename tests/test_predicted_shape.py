"""The predicted pitch stops drawing back sevens.

FPL codes wing-backs and pushed-up full-backs as defenders, so a predicted
eleven grouped by its FPL codes can put seven men in the defensive line, a
shape no team has ever played, drawn straight off the bottom of the pitch.
The line is now capped at five, and the overflow moves into midfield,
preferring whoever the league's own team sheets last showed actually
playing there. A promoted player keeps his D badge: he is still a
defender, just not drawn in a back seven.
"""

from types import SimpleNamespace

from foulgorithm.publish.player_round import _predicted_shape
from foulgorithm.store import positions


def sel(display, position="DEF", full=None):
    return SimpleNamespace(display=display, full=full or f"{display} Full", position=position)


def eleven(defenders=7, mids=2, forwards=1):
    out = [sel("Keeper", "GKP")]
    out += [sel(f"D{i}") for i in range(defenders)]
    out += [sel(f"M{i}", "MID") for i in range(mids)]
    out += [sel(f"F{i}", "FWD") for i in range(forwards)]
    return out


class TestTheCap:
    def test_a_back_seven_becomes_a_back_five(self):
        shape = _predicted_shape(eleven())
        assert [len(line) for line in shape["lines"]] == [1, 5, 4, 1]

    def test_a_back_five_is_left_alone(self):
        shape = _predicted_shape(eleven(defenders=5, mids=4))
        assert [len(line) for line in shape["lines"]] == [1, 5, 4, 1]

    def test_a_promoted_defender_keeps_his_badge(self):
        shape = _predicted_shape(eleven())
        midfield = shape["lines"][2]
        assert sum(1 for s in midfield if s["position"] == "D") == 2

    def test_without_role_memory_the_last_listed_defenders_move_up(self):
        shape = _predicted_shape(eleven())
        back = {s["player"] for s in shape["lines"][1]}
        assert back == {"D0", "D1", "D2", "D3", "D4"}


class TestRoleMemory:
    def test_a_player_last_seen_in_midfield_moves_up_first(self):
        roles = {positions.norm("D1 Full"): "Centre Defensive Midfielder"}
        shape = _predicted_shape(eleven(), roles=roles)
        back = {s["player"] for s in shape["lines"][1]}
        assert "D1" not in back

    def test_a_wide_defender_moves_before_an_unseen_one(self):
        roles = {
            positions.norm("D0 Full"): "Right Full Back",
            positions.norm("D1 Full"): "Right Wing Back",
        }
        shape = _predicted_shape(eleven(defenders=6, mids=3), roles=roles)
        back = {s["player"] for s in shape["lines"][1]}
        # One must go; both wide players outrank the unseen, and of the two
        # wide players the later-listed goes first.
        assert back == {"D0", "D2", "D3", "D4", "D5"}

    def test_a_known_centre_back_stays_while_anyone_else_can_go(self):
        roles = {positions.norm(f"D{i} Full"): "Centre Central Defender" for i in (5, 6)}
        shape = _predicted_shape(eleven(), roles=roles)
        back = {s["player"] for s in shape["lines"][1]}
        assert {"D5", "D6"} <= back


class TestTheStore:
    def test_roles_round_trip_with_accents_folded(self, tmp_path):
        state = tmp_path / "positions_seen.json"
        lineup = SimpleNamespace(
            lines=[
                [SimpleNamespace(name="Gabriel Magalhães", detail="Centre Central Defender")],
                [SimpleNamespace(name="Daniel Muñoz", detail="Right Full Back")],
            ]
        )
        positions.remember({"Palace|A v B": lineup}, path=state)
        roles = positions.load(path=state)
        assert positions.role_for(roles, "Daniel Munoz") == "Right Full Back"
        assert positions.role_for(roles, "gabriel magalhaes") == "Centre Central Defender"

    def test_a_later_sighting_replaces_the_earlier_role(self, tmp_path):
        state = tmp_path / "positions_seen.json"
        first = SimpleNamespace(lines=[[SimpleNamespace(name="Joe", detail="Right Full Back")]])
        later = SimpleNamespace(lines=[[SimpleNamespace(name="Joe", detail="Right Midfielder")]])
        positions.remember({"a": first}, path=state)
        positions.remember({"b": later}, path=state)
        assert positions.role_for(positions.load(path=state), "Joe") == "Right Midfielder"

    def test_an_empty_fetch_writes_nothing(self, tmp_path):
        state = tmp_path / "positions_seen.json"
        positions.remember({}, path=state)
        assert not state.exists()
