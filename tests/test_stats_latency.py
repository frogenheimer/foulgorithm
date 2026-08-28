"""The latency probe measures WHEN the league's season totals move, so the
settle delays can be set from evidence rather than caution. It only ever
reads and logs; nothing it writes feeds grading."""

from foulgorithm.jobs import stats_latency


class TestMoved:
    BASELINE = {
        "A. One": {"fouls": 10.0, "was_fouled": 4.0, "appearances": 3.0, "mins_played": 270.0},
        "B. Two": {"fouls": 2.0, "was_fouled": 1.0, "appearances": 3.0, "mins_played": 240.0},
    }

    def test_counts_players_whose_totals_rose(self):
        current = {
            "A. One": {"fouls": 12.0, "was_fouled": 4.0, "appearances": 4.0, "mins_played": 360.0},
            "B. Two": {"fouls": 2.0, "was_fouled": 1.0, "appearances": 3.0, "mins_played": 240.0},
        }
        held = stats_latency.moved(self.BASELINE, current)
        assert held == {"players": 1, "appearances": 1}

    def test_a_debutant_counts_as_moved(self):
        current = dict(
            self.BASELINE,
            **{
                "C. New": {"fouls": 1.0, "was_fouled": 0.0, "appearances": 1.0, "mins_played": 90.0}
            },
        )
        held = stats_latency.moved(self.BASELINE, current)
        assert held == {"players": 1, "appearances": 1}

    def test_nothing_moved_is_zero(self):
        held = stats_latency.moved(self.BASELINE, dict(self.BASELINE))
        assert held == {"players": 0, "appearances": 0}

    def test_a_foul_moving_without_an_appearance_is_counted_apart(self):
        # The tables are separate feeds, so fouls can post before appearances.
        current = {
            "A. One": {"fouls": 12.0, "was_fouled": 4.0, "appearances": 3.0, "mins_played": 270.0},
            "B. Two": self.BASELINE["B. Two"],
        }
        held = stats_latency.moved(self.BASELINE, current)
        assert held == {"players": 1, "appearances": 0}
