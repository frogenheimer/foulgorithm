"""Predicting the eleven, which is the input every player bet depends on.

Ranking a club's players on this season's start count scores 63.1% of slots
across 1,058 team-matches. Taking whoever started the last match scores 76.5%,
and topping that up from the counter where the last eleven is short scores
78.1%. A fifteen-point gain for a simpler rule.

Availability is applied on top: FPL carries club-sourced injury and suspension
status, so someone ruled out cannot survive into a prediction just because he
started last week.
"""

import pandas as pd
import pytest

from foulgorithm.features import expected_xi


def _history(rows):
    """rows: (player, days_ago, minutes)"""
    now = pd.Timestamp("2026-08-20", tz="UTC")
    return pd.DataFrame(
        [
            {
                "player": p,
                "team": "Arsenal",
                "kickoff_utc": now - pd.Timedelta(days=d),
                "known_at": now - pd.Timedelta(days=d),
                "minutes": m,
            }
            for p, d, m in rows
        ]
    )


AS_OF = pd.Timestamp("2026-08-21", tz="UTC")
ELEVEN = [(f"p{i}", 7, 90) for i in range(11)]


class TestLastEleven:
    def test_it_takes_whoever_started_the_last_match(self):
        h = _history(ELEVEN + [("older", 30, 90)])
        assert expected_xi.last_eleven(h, "Arsenal", AS_OF) == {f"p{i}" for i in range(11)}

    def test_a_substitute_is_not_a_starter(self):
        # 20 minutes is a cameo. The bet is on someone playing the match.
        h = _history(ELEVEN + [("sub", 7, 20)])
        assert "sub" not in expected_xi.last_eleven(h, "Arsenal", AS_OF)

    def test_it_ignores_anything_after_the_cutoff(self):
        # Leakage guard. A match that has not happened yet cannot inform a
        # prediction about one that also has not.
        h = _history(ELEVEN + [("future", -3, 90)])
        assert "future" not in expected_xi.last_eleven(h, "Arsenal", AS_OF)

    def test_no_history_gives_nothing_rather_than_a_guess(self):
        assert expected_xi.last_eleven(_history([]), "Arsenal", AS_OF) == set()


class TestAssemble:
    def test_the_last_eleven_leads(self):
        picked = expected_xi.assemble(
            last=[f"p{i}" for i in range(11)],
            fallback=["x", "y", "z"],
            unavailable=set(),
        )
        assert picked == [f"p{i}" for i in range(11)]

    def test_an_unavailable_player_is_dropped_and_replaced(self):
        picked = expected_xi.assemble(
            last=[f"p{i}" for i in range(11)],
            fallback=["backup"],
            unavailable={"p3"},
        )
        assert "p3" not in picked
        assert "backup" in picked
        assert len(picked) == 11

    def test_a_short_last_eleven_is_topped_up_in_order(self):
        picked = expected_xi.assemble(last=["a", "b"], fallback=["c", "d", "e"], unavailable=set())
        assert picked[:2] == ["a", "b"]
        assert picked[2:] == ["c", "d", "e"]

    def test_it_never_repeats_a_player(self):
        picked = expected_xi.assemble(last=["a", "b"], fallback=["b", "c"], unavailable=set())
        assert picked == ["a", "b", "c"]

    def test_with_nothing_to_go_on_it_returns_the_fallback(self):
        assert expected_xi.assemble(last=[], fallback=["a", "b"], unavailable=set()) == ["a", "b"]
