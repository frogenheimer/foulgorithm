"""Context factors from the match store, pointed the right way round.

For fouls COMMITTED the opponent's relevant property is how many fouls sides
give away against them; for fouls DRAWN it is how many the opponent commits.
Advisor 2 flagged direction as the dangerous conceptual bug in any opponent
factor, so both directions are pinned here with data where they differ
sharply, along with the as-of gate and the crosswalk hop into the store's
name space.
"""

import pandas as pd
import pytest

from foulgorithm.features.team_context import MatchContextSource, fixture_name
from foulgorithm.models.player_models import PlayerFouledModel, PlayerFoulModel


def matches(rows):
    frame = pd.DataFrame(
        rows,
        columns=[
            "kickoff_utc",
            "home_team_raw",
            "away_team_raw",
            "home_fouls",
            "away_fouls",
            "referee_raw",
        ],
    )
    frame["kickoff_utc"] = pd.to_datetime(frame["kickoff_utc"], utc=True)
    frame["known_at"] = frame["kickoff_utc"] + pd.Timedelta(hours=3)
    frame["total_fouls"] = frame["home_fouls"] + frame["away_fouls"]
    return frame


def league(n=40, fouls=10.0, referee="Common Ref"):
    """A balanced backdrop so the league average sits exactly at `fouls`."""
    return [
        (
            f"2025-{1 + i % 8:02d}-{1 + i % 27:02d}",
            f"Filler {i % 6}",
            f"Filler {(i + 3) % 6}",
            fouls,
            fouls,
            referee,
        )
        for i in range(n)
    ]


AS_OF = pd.Timestamp("2025-12-01", tz="UTC")


class TestDirection:
    def build(self):
        # Magnet FC's opponents commit 16 a match against them while Magnet
        # commit only 6, on a league backdrop of 10 a side. The two markets
        # must read opposite sides of that asymmetry.
        rows = league() + [
            (f"2025-{m:02d}-14", "Magnet FC", f"Filler {m % 6}", 6.0, 16.0, "Common Ref")
            for m in range(3, 11)
        ]
        return MatchContextSource(matches(rows))

    def test_committed_market_reads_what_opponents_concede_against_them(self):
        source = self.build()
        raw, effective = source.opponent_factor("Magnet FC", AS_OF, "player_fouls_committed")
        assert raw > 1.2
        assert effective > 5

    def test_drawn_market_reads_what_they_commit(self):
        source = self.build()
        raw, _ = source.opponent_factor("Magnet FC", AS_OF, "player_fouls_drawn")
        assert raw < 0.9

    def test_the_two_directions_are_not_the_same_number(self):
        source = self.build()
        committed, _ = source.opponent_factor("Magnet FC", AS_OF, "player_fouls_committed")
        drawn, _ = source.opponent_factor("Magnet FC", AS_OF, "player_fouls_drawn")
        assert committed != drawn


class TestTheGates:
    def test_the_future_is_invisible(self):
        rows = league() + [
            ("2025-12-20", "Magnet FC", "Filler 1", 6.0, 30.0, "Common Ref"),
        ]
        source = MatchContextSource(matches(rows))
        raw, effective = source.opponent_factor("Magnet FC", AS_OF, "player_fouls_committed")
        assert effective == 0.0
        assert raw == pytest.approx(1.0)

    def test_an_unknown_club_is_the_prior_with_zero_matches_not_a_silent_one(self):
        source = MatchContextSource(matches(league()))
        raw, effective = source.opponent_factor("Nowhere Town", AS_OF, "player_fouls_committed")
        assert raw == pytest.approx(1.0)
        assert effective == 0.0

    def test_archive_spelling_reaches_the_store_spelling(self):
        assert fixture_name("Manchester United") == "Man United"
        assert fixture_name("Arsenal") == "Arsenal"

    def test_a_thin_referee_barely_moves_from_one(self):
        rows = league() + [("2025-11-30", "Filler 0", "Filler 1", 15.0, 15.0, "Cardhappy")]
        source = MatchContextSource(matches(rows))
        factor, effective = source.referee_factor("Cardhappy", AS_OF)
        assert 1.0 < factor < 1.1
        assert effective == pytest.approx(1.0, abs=0.1)


class TestModelIntegration:
    def history(self):
        dates = pd.to_datetime([f"2025-{m:02d}-05" for m in range(3, 11)], utc=True)
        return pd.DataFrame(
            {
                "player": "Steady Mid",
                "team": "Filler 0",
                "opponent": "Filler 1",
                "kickoff_utc": dates,
                "known_at": dates + pd.Timedelta(hours=3),
                "season": 2025,
                "position": "DM",
                "minutes": 90.0,
                "fouls_committed": 1.0,
                "fouls_drawn": 1.0,
            }
        )

    def test_the_character_weight_still_scales_the_deviation(self):
        rows = league() + [
            (f"2025-{m:02d}-14", "Magnet FC", f"Filler {m % 6}", 6.0, 16.0, "Common Ref")
            for m in range(3, 11)
        ]
        source = MatchContextSource(matches(rows))

        timid = PlayerFoulModel(opponent_weight=0.4)
        bold = PlayerFoulModel(opponent_weight=1.6)
        for model in (timid, bold):
            model.fit(self.history())
            model.use_match_context(source)

        timid_factor = timid.opponent_factor("Magnet FC", AS_OF)
        bold_factor = bold.opponent_factor("Magnet FC", AS_OF)
        assert 1.0 < timid_factor < bold_factor

    def test_without_a_source_the_archive_path_is_untouched(self):
        model = PlayerFoulModel()
        model.fit(self.history())
        factor = model.opponent_factor("Filler 1", AS_OF)
        assert factor > 0

    def test_a_promoted_club_keeps_its_second_tier_fallback(self):
        """The store has no top-flight rows for a promoted club, and 1.0 from
        an empty lookup is the failure this project exists not to make. Below
        the evidence floor the Championship prior still speaks."""
        source = MatchContextSource(matches(league()))
        model = PlayerFoulModel()
        model.fit(self.history())
        model.use_match_context(source)

        called = {}

        def fake_promoted(club):
            called["club"] = club
            return 1.04

        model._promoted_opponent_factor = fake_promoted
        assert model.opponent_factor("Coventry", AS_OF) == pytest.approx(1.04)
        assert called["club"] == "Coventry"

    def test_an_established_club_does_not_touch_the_promoted_path(self):
        rows = league() + [
            (f"2025-{m:02d}-14", "Magnet FC", f"Filler {m % 6}", 6.0, 16.0, "Common Ref")
            for m in range(3, 11)
        ]
        source = MatchContextSource(matches(rows))
        model = PlayerFoulModel()
        model.fit(self.history())
        model.use_match_context(source)
        model._promoted_opponent_factor = lambda club: pytest.fail(
            "an established club must not reach the promoted fallback"
        )
        assert model.opponent_factor("Magnet FC", AS_OF) > 1.0

    def test_drawn_model_reads_the_drawn_direction_through_the_same_source(self):
        rows = league() + [
            (f"2025-{m:02d}-14", "Magnet FC", f"Filler {m % 6}", 6.0, 16.0, "Common Ref")
            for m in range(3, 11)
        ]
        source = MatchContextSource(matches(rows))
        model = PlayerFouledModel(opponent_weight=1.0)
        model.fit(self.history())
        model.use_match_context(source)
        assert model.opponent_factor("Magnet FC", AS_OF) < 1.0
