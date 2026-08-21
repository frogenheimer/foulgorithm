"""The five characters must be genuinely different, and none may be stupid.

These tests enforce the rule that keeps the bake-off honest: a character may be
wrong, but never deliberately bad. If a personality stops being a defensible
research philosophy and becomes a handicap, a test here should fail.
"""

import numpy as np
import pytest

from foulgorithm.backtest import harness
from foulgorithm.characters import base as characters
from foulgorithm.models import character_models as cm
from foulgorithm.models.match_models import LeagueMean
from tests.test_leakage import synthetic


class TestCast:
    def test_five_characters(self):
        assert len(characters.ALL) == 5

    def test_ids_are_unique_and_stable(self):
        ids = [c.id for c in characters.ALL]
        assert ids == ["alan", "lily", "valentina", "tayler", "bdog"]

    def test_every_character_declares_a_weakness(self):
        # The site states each one's blind spot. A character without a named
        # weakness is marketing, not a model.
        for c in characters.ALL:
            assert c.weakness.strip()
            assert c.edge.strip()
            assert c.on_losing.strip()

    def test_unknown_character_raises(self):
        with pytest.raises(KeyError):
            characters.get("kevin")


class TestModels:
    def test_one_model_per_character(self):
        model_ids = {m.character_id for m in cm.build_all()}
        assert model_ids == {c.id for c in characters.ALL}

    def test_each_has_its_own_configuration(self):
        # If two characters share every parameter they are not competing, they
        # are the same model wearing two names.
        configs = [tuple(sorted(m.config().items())) for m in cm.build_all()]
        assert len(set(configs)) == len(configs)

    def test_memory_lengths_are_meaningfully_different(self):
        by_id = {m.character_id: m.half_life_days for m in cm.build_all()}
        # Anger remembers least, terror remembers longest.
        assert by_id["alan"] < by_id["bdog"] < by_id["tayler"]
        assert by_id["lily"] > by_id["alan"] * 5

    def test_confidence_matches_temperament(self):
        by_id = {m.character_id: m.dispersion_scale for m in cm.build_all()}
        # Alan is overconfident, Tayler hedges. Narrower is more confident.
        assert by_id["alan"] < by_id["tayler"]


class TestBehaviour:
    """Fit on real-shaped synthetic data and check the personalities show up."""

    @pytest.fixture(scope="class")
    @classmethod
    def fitted(cls):
        df = synthetic(1200)
        models = cm.build_all()
        for m in models:
            m.fit(df)
        return df, models

    def test_all_produce_valid_distributions(self, fitted):
        df, models = fitted
        upcoming = df.tail(10)
        for m in models:
            for dist in m.predict(upcoming):
                total = sum(dist.pmf(k) for k in range(0, 61))
                assert total == pytest.approx(1.0, abs=1e-6)
                assert dist.mean() > 0
                assert 0.0 <= dist.prob_over(22.5) <= 1.0

    def test_characters_disagree(self, fitted):
        df, models = fitted
        upcoming = df.tail(10)
        means = {m.character_id: [d.mean() for d in m.predict(upcoming)] for m in models}
        # On identical fixtures they must not all land on the same number.
        spread = np.std([np.mean(v) for v in means.values()])
        assert spread > 0.05, f"characters are indistinguishable, spread={spread:.4f}"

    def test_none_is_absurd(self, fitted):
        """No character may predict something football cannot produce.

        This is the guard against a personality becoming a handicap.
        """
        df, models = fitted
        upcoming = df.tail(20)
        league = df["total_fouls"].mean()
        for m in models:
            for dist in m.predict(upcoming):
                assert league * 0.5 < dist.mean() < league * 1.6, (
                    f"{m.character_id} predicted {dist.mean():.1f} against a league mean of {league:.1f}"
                )

    def test_tayler_hugs_the_average_hardest(self, fitted):
        df, models = fitted
        upcoming = df.tail(20)
        league = df["total_fouls"].mean()
        by_id = {m.character_id: m for m in models}
        drift = {
            cid: float(np.mean([abs(d.mean() - league) for d in by_id[cid].predict(upcoming)]))
            for cid in ("tayler", "alan")
        }
        # Terror shrinks toward the mean, anger runs from it.
        assert drift["tayler"] < drift["alan"]


class TestCompetition:
    def test_all_five_score_on_the_same_data(self):
        df = synthetic(900)
        results = harness.walk_forward(
            [LeagueMean(), *cm.build_all()], df, start="2020-21", min_train=300
        )
        assert len(results) == 6
        assert len({r.model_id for r in results}) == 6
        for r in results:
            assert r.n > 0
            assert np.isfinite(r.log_loss)
