"""Leakage defences.

The 2025 version's only evaluation predicted matchweeks using season averages
computed from files that already contained those matchweeks, and reported a win
rate that meant nothing. These tests exist so that cannot happen again.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from foulgorithm.backtest import harness
from foulgorithm.features import match_features as mf
from foulgorithm.models.base import CountDistribution

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def synthetic(n: int = 900, seed: int = 3) -> pd.DataFrame:
    """Matches whose foul counts are pure noise around a constant.

    Nothing here is predictable beyond the mean. Any model that beats the mean
    on this data is reading the future.
    """
    rng = np.random.default_rng(seed)
    teams = [f"Team{i}" for i in range(20)]
    rows = []
    for i in range(n):
        kickoff = BASE + timedelta(days=i * 3)
        home, away = rng.choice(teams, size=2, replace=False)
        rows.append(
            {
                "season": f"{2019 + i // 380}-{(2020 + i // 380) % 100:02d}",
                "kickoff_utc": kickoff,
                "known_at": kickoff + timedelta(hours=3),
                "home_team_raw": home,
                "away_team_raw": away,
                "referee_raw": f"Ref{rng.integers(0, 8)}",
                "home_fouls": int(rng.poisson(11)),
                "away_fouls": int(rng.poisson(11)),
                # Cards are here because Valentina models them rather than
                # fouls. Also pure noise, so the canary still has no signal.
                "home_yellows": int(rng.poisson(1.9)),
                "away_yellows": int(rng.poisson(2.1)),
                "home_reds": int(rng.poisson(0.06)),
                "away_reds": int(rng.poisson(0.07)),
                "home_shots": int(rng.poisson(12)),
                "away_shots": int(rng.poisson(11)),
                "odds_home": None,
                "odds_draw": None,
                "odds_away": None,
            }
        )
    df = pd.DataFrame(rows)
    df["total_fouls"] = df["home_fouls"] + df["away_fouls"]
    return df


class TestVisibility:
    def test_visible_excludes_the_future(self):
        df = synthetic(100)
        as_of = df["kickoff_utc"].iloc[50]
        past = mf.visible(df, as_of)
        assert (past["known_at"] <= as_of).all()
        assert len(past) < len(df)

    def test_a_match_cannot_see_itself(self):
        # known_at is kickoff plus 3 hours, so a match is never visible to a
        # prediction made at its own kickoff.
        df = synthetic(100)
        as_of = df["kickoff_utc"].iloc[50]
        past = mf.visible(df, as_of)
        assert as_of not in set(past["kickoff_utc"])

    def test_context_uses_only_visible_rows(self):
        df = synthetic(400)
        as_of = df["kickoff_utc"].iloc[200]
        ctx = mf.build_context(df, "Team1", "Team2", "Ref1", as_of)

        # Corrupting the future must not change a prediction about the present.
        poisoned = df.copy()
        future = poisoned["known_at"] > as_of
        poisoned.loc[future, "home_fouls"] = 99
        poisoned.loc[future, "away_fouls"] = 99
        poisoned["total_fouls"] = poisoned["home_fouls"] + poisoned["away_fouls"]

        after = mf.build_context(poisoned, "Team1", "Team2", "Ref1", as_of)
        assert ctx.league_fouls == pytest.approx(after.league_fouls)
        assert ctx.home_commit == pytest.approx(after.home_commit)
        assert ctx.referee_factor == pytest.approx(after.referee_factor)


class TestCanary:
    """A leaking model must be caught on data with no signal in it."""

    def test_honest_models_cannot_beat_noise(self):
        from foulgorithm.models.match_models import LeagueMean, TeamRates

        df = synthetic(900)
        results = harness.walk_forward([LeagueMean, TeamRates], df, start="2020-21", min_train=300)
        assert results, "harness produced no results"
        best, worst = min(r.log_loss for r in results), max(r.log_loss for r in results)
        # On pure noise every honest model collapses onto the same score.
        assert worst - best < 0.05, f"suspicious spread on noise: {worst - best:.4f}"

    def test_a_cheating_model_is_caught(self):
        class Cheater:
            id, version, market = "cheater", "1.0.0", "match_total_fouls"

            def fit(self, train):
                self._train = train

            def config(self):
                return {}

            def predict(self, context):
                # Reads the answer it is being asked to predict.
                out = []
                for _, row in context.iterrows():
                    pmf = np.full(61, 1e-9)
                    pmf[int(row["total_fouls"])] = 1.0
                    out.append(CountDistribution(pmf))
                return out

        from foulgorithm.models.match_models import LeagueMean

        df = synthetic(900)
        results = harness.walk_forward([LeagueMean, Cheater], df, start="2020-21", min_train=300)
        scores = {r.model_id: r.log_loss for r in results}
        # If a model that reads the target does not stand out, the harness is broken.
        assert scores["cheater"] < scores["league_mean"] / 10


class TestShrinkage:
    def test_unknown_team_lands_on_the_league_prior(self):
        # A promoted club with no history must not be modelled as extreme.
        df = synthetic(400)
        as_of = df["kickoff_utc"].iloc[300]
        ctx = mf.build_context(df, "Coventry", "Hull", None, as_of)
        assert ctx.home_commit == pytest.approx(1.0)
        assert ctx.away_commit == pytest.approx(1.0)
        assert ctx.home_matches == 0.0

    def test_time_decay_favours_recent_matches(self):
        df = synthetic(600)
        as_of = df["kickoff_utc"].iloc[-1] + timedelta(days=1)
        fast = mf.build_context(df, "Team1", "Team2", None, as_of, half_life_days=30)
        slow = mf.build_context(df, "Team1", "Team2", None, as_of, half_life_days=100000)
        assert fast.home_matches < slow.home_matches


class TestMismatch:
    def test_even_game_is_zero(self):
        assert mf.mismatch_from_odds(2.6, 3.4, 2.6) == pytest.approx(0.0, abs=1e-9)

    def test_walkover_is_large(self):
        assert mf.mismatch_from_odds(1.2, 7.0, 13.0) > 0.6

    def test_missing_odds_is_neutral(self):
        assert mf.mismatch_from_odds(None, None, None) == 0.0

    def test_margin_is_removed(self):
        # Probabilities must sum to 1 after stripping the overround, so a
        # symmetric market reads as even however large the margin.
        assert mf.mismatch_from_odds(1.9, 3.0, 1.9) == pytest.approx(0.0, abs=1e-9)
