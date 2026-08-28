"""Minutes drive everything, and averaging them hides a bimodal truth.

A rotation player who alternates 90 minutes and 0 has an average of 45. He has
never once played 45 minutes. Feeding that average into a single distribution
prices him as a steady half-match player rather than as what he is: often
absent, occasionally a full starter.

The mean is unaffected, which is why this never showed up in a bias check. The
shape is badly wrong, and the shape is what a bet settles on.
"""

import pandas as pd
import pytest

from foulgorithm.models.player_models import PlayerFoulModel


def _history(pattern, player="rotation guy", start="2024-01-01"):
    """Build a match log where `pattern` is that player's minutes, most recent last."""
    days = pd.date_range(start, periods=len(pattern), freq="7D")
    rows = []
    for day, mins in zip(days, pattern, strict=False):
        rows.append(
            {
                "player": player,
                "team": "Team A",
                "opponent": "Team B",
                "position": "CM",
                "minutes": float(mins),
                "fouls_committed": round(mins / 90.0 * 2.0),
                "known_at": day,
                "kickoff": day,
            }
        )
        # A steady team-mate, so league and position priors are well defined.
        rows.append(
            {
                "player": "ever present",
                "team": "Team A",
                "opponent": "Team B",
                "position": "CM",
                "minutes": 90.0,
                "fouls_committed": 2,
                "known_at": day,
                "kickoff": day,
            }
        )
    return pd.DataFrame(rows)


AS_OF = pd.Timestamp("2024-12-01")


class TestProfileShape:
    def test_ever_present_starter_is_nearly_certain_to_start(self):
        m = PlayerFoulModel()
        m.fit(_history([90] * 12, player="ever present"))
        p = m.minutes_profile("ever present", AS_OF)
        assert p.p_start > 0.85
        assert p.p_unused < 0.10
        assert p.minutes_if_start > 80.0

    def test_alternating_player_is_not_a_half_match_player(self):
        m = PlayerFoulModel()
        m.fit(_history([90, 0] * 6))
        p = m.minutes_profile("rotation guy", AS_OF)

        # The old model said 45 minutes. The truth is a coin flip on 90.
        assert 0.3 < p.p_start < 0.7
        assert p.p_unused > 0.3
        assert p.minutes_if_start > 80.0, "when he plays, he plays a full match"

    def test_expected_minutes_still_equals_the_profile_mean(self):
        # The two-stage split must not move the mean, only the shape. If it
        # moves the mean it is a different model, not a better description.
        m = PlayerFoulModel()
        m.fit(_history([90, 0, 90, 0, 90, 90, 0, 90]))
        p = m.minutes_profile("rotation guy", AS_OF)
        assert p.mean_minutes() == pytest.approx(m.expected_minutes("rotation guy", AS_OF), abs=3.0)

    def test_unseen_player_gets_the_starter_prior_not_zero(self):
        # Regression guard. Returning nothing for an unseen player is how a
        # promoted club came to show a quarter of Manchester United's fouls.
        m = PlayerFoulModel()
        m.fit(_history([90] * 10, player="ever present"))
        p = m.minutes_profile("brand new signing", AS_OF)
        assert p.mean_minutes() > 30.0
        assert p.p_start > 0.5


class TestMixtureShape:
    def test_rotation_risk_raises_the_chance_of_zero_fouls(self):
        m = PlayerFoulModel()
        m.fit(_history([90, 0] * 6))
        dist, _ = m.predict_one("rotation guy", "Team B", AS_OF)

        # He is unused about half the time, and an unused player commits no
        # fouls. Nothing below that floor is defensible.
        assert dist.pmf(0) > 0.4

    def test_the_mixture_keeps_the_mean_it_was_given(self):
        m = PlayerFoulModel()
        m.fit(_history([90, 0] * 6))
        dist, why = m.predict_one("rotation guy", "Team B", AS_OF)
        assert dist.mean() == pytest.approx(why["expected_fouls"], rel=0.05)

    def test_an_ever_present_is_barely_changed(self):
        # The fix must be inert where it does not apply, or it is a change to
        # every prediction dressed up as a fix to one case.
        m = PlayerFoulModel()
        m.fit(_history([90] * 12, player="ever present"))
        dist, _ = m.predict_one("ever present", "Team B", AS_OF)
        single = m._single_distribution(dist.mean())
        for k in range(6):
            assert dist.pmf(k) == pytest.approx(single.pmf(k), abs=0.05)

    def test_probabilities_still_sum_to_one(self):
        m = PlayerFoulModel()
        m.fit(_history([90, 0, 20, 0, 90, 45] * 2))
        dist, _ = m.predict_one("rotation guy", "Team B", AS_OF)
        total = sum(dist.pmf(k) for k in range(0, 40))
        assert total == pytest.approx(1.0, abs=1e-6)
