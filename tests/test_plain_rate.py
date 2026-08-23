"""Two different numbers that both get called "expected".

What the site shows is the model's expected value for THIS match: the player's
shrunk, time-decayed rate, times his expected minutes, times the opponent and
the referee, read off the fitted distribution. It is not an average of anything.

That is the right number and it is worth being able to check against the plain
one, which is simply the fouls he has committed divided by the nineties he has
played. Where the two disagree, the difference is the model's opinion, and a
reader should be able to see the size of it.
"""

import pandas as pd
import pytest

from foulgorithm.models import player_models as pm


def history(rows):
    return pd.DataFrame(
        [
            {
                "player": name, "team": "T", "opponent": "O", "venue": "H",
                "kickoff_utc": pd.Timestamp(day, tz="UTC"),
                "known_at": pd.Timestamp(day, tz="UTC"),
                "season": "2025-26", "position": "MF", "minutes": mins,
                "fouls_committed": fouls, "fouls_drawn": 1, "yellows": 0, "reds": 0,
                "tackles_won": 1, "interceptions": 1, "source": "test",
            }
            for name, day, mins, fouls in rows
        ]
    )


AS_OF = pd.Timestamp("2026-02-01", tz="UTC")


class TestThePlainRate:
    def test_it_is_fouls_divided_by_nineties(self):
        model = pm.build("tayler")
        model.fit(history([("A", f"2026-01-{d:02d}", 90, 2) for d in range(1, 11)]))
        rate, nineties = model.plain_rate("A", AS_OF)
        assert rate == pytest.approx(2.0)
        assert nineties == pytest.approx(10.0)

    def test_part_matches_count_as_part_nineties(self):
        model = pm.build("tayler")
        model.fit(history([("A", "2026-01-01", 45, 1), ("A", "2026-01-02", 45, 1)]))
        rate, nineties = model.plain_rate("A", AS_OF)
        assert nineties == pytest.approx(1.0)
        assert rate == pytest.approx(2.0)

    def test_it_does_not_shrink(self):
        """One appearance reports what happened, however little that is worth.

        This is the number the shrunk one is meant to be compared against, so
        shrinking it too would leave nothing to compare.
        """
        model = pm.build("tayler")   # the heaviest shrinkage of the five
        # Other players, so the position prior is something other than his own
        # rate. With one player in the training data the prior IS his rate and
        # shrinking toward it changes nothing.
        crowd = [(f"P{i}", f"2026-01-{d:02d}", 90, 1) for i in range(12) for d in range(1, 9)]
        model.fit(history([("A", "2026-01-01", 90, 5), *crowd]))
        plain, _ = model.plain_rate("A", AS_OF)
        shrunk, _ = model.player_rate("A", AS_OF)
        assert plain == pytest.approx(5.0)
        assert shrunk < 2.0, "the model's own rate should pull hard toward the prior"

    def test_it_does_not_decay(self):
        """Old matches count the same, which is the point of a plain average."""
        old = pm.build("alan")       # a 70-day half-life
        old.fit(history([("A", "2024-01-01", 90, 4), ("A", "2026-01-01", 90, 4)]))
        plain, _ = old.plain_rate("A", AS_OF)
        assert plain == pytest.approx(4.0)

    def test_an_unknown_player_has_no_plain_rate(self):
        model = pm.build("tayler")
        model.fit(history([("A", "2026-01-01", 90, 1)]))
        assert model.plain_rate("Nobody", AS_OF) == (None, 0.0)

    def test_a_player_with_no_minutes_has_no_rate_rather_than_infinity(self):
        model = pm.build("tayler")
        model.fit(history([("A", "2026-01-01", 0, 0), ("B", "2026-01-01", 90, 1)]))
        assert model.plain_rate("A", AS_OF) == (None, 0.0)

    def test_fitting_on_a_history_with_no_minutes_refuses(self):
        """It divided by zero and made the league rate NaN, silently.

        A NaN league rate poisons every prior and every shrunk rate downstream
        without raising anywhere, so the numbers come out wrong rather than
        missing. There is no league rate to be had, and saying so is the only
        honest option.
        """
        model = pm.build("tayler")
        with pytest.raises(ValueError, match="no minutes"):
            model.fit(history([("A", "2026-01-01", 0, 0)]))

    def test_it_respects_the_as_of(self):
        model = pm.build("tayler")
        model.fit(history([("A", "2026-01-01", 90, 1), ("A", "2026-03-01", 90, 9)]))
        early, _ = model.plain_rate("A", pd.Timestamp("2026-02-01", tz="UTC"))
        late, _ = model.plain_rate("A", pd.Timestamp("2026-04-01", tz="UTC"))
        assert early == pytest.approx(1.0)
        assert late == pytest.approx(5.0)
