"""Settle refreshes the league table it just changed.

The table lives in players.json and was only ever recomputed by a full
publish, so a Saturday's grading did not reach The five until the next
lineups wake, and Monday's round-closing grade waited until FRIDAY. Settle
now rewrites the standings and settled cards in place, touching nothing
else in the payload."""

import json

from foulgorithm.jobs import settle


def test_refresh_rewrites_standings_and_settled_cards_only(tmp_path, monkeypatch):
    path = tmp_path / "players.json"
    path.write_text(json.dumps({
        "generatedAt": "2026-08-25T02:42:56+00:00",
        "board": [{"home": "A", "away": "B"}],
        "standings": [{"id": "alan", "points": 0}, {"id": "lily", "points": 0}],
        "settledCards": {},
    }))

    from foulgorithm.publish import player_round
    monkeypatch.setattr(player_round, "_standings", lambda ids: [{"id": i, "points": 3} for i in ids])
    monkeypatch.setattr(player_round, "_settled_cards", lambda: {"A v B": {"version": 1, "options": []}})

    assert settle.refresh_table(path) is True
    held = json.loads(path.read_text())
    assert [r["points"] for r in held["standings"]] == [3, 3]
    assert held["settledCards"] == {"A v B": {"version": 1, "options": []}}
    assert held["board"] == [{"home": "A", "away": "B"}]
    assert held["generatedAt"] == "2026-08-25T02:42:56+00:00"


def test_refresh_is_a_no_op_without_a_payload(tmp_path):
    assert settle.refresh_table(tmp_path / "absent.json") is False
