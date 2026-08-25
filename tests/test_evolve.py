"""magicIan's evolution must be auditable, bounded and honest.

He is the only competitor whose dials change, so the rules that keep the
league fair for him are structural: every generation appends to a lineage
that never rewrites, every gene stays inside named bounds, the current
champion always defends his seat in the population, the rivals' own dial
sets are always in the gene pool (learning from the others is the point),
and the same generation number always breeds the same candidates, so a
re-run cannot quietly produce a different Ian.
"""

import json

from foulgorithm.models import evolve


def fitness_prefers_long_memory(genome, **_):
    """A fake evaluator: the closer half_life_days is to 1200, the better."""
    return abs(genome["half_life_days"] - 1200)


class TestGenome:
    def test_the_seed_is_the_genome_until_evolution_starts(self, tmp_path):
        assert evolve.current_genome(tmp_path / "none.jsonl") == evolve.SEED

    def test_every_gene_is_clamped_to_its_bounds(self):
        wild = {k: 1e9 for k in evolve.SEED}
        clamped = evolve.clamp(wild)
        for gene, (lo, hi) in evolve.GENE_BOUNDS.items():
            assert lo <= clamped[gene] <= hi

    def test_mutation_stays_inside_the_bounds(self):
        import random

        rng = random.Random(7)
        for _ in range(50):
            child = evolve.mutate(evolve.SEED, rng)
            for gene, (lo, hi) in evolve.GENE_BOUNDS.items():
                assert lo <= child[gene] <= hi


class TestTheStep:
    def test_the_winner_is_appended_and_becomes_the_genome(self, tmp_path):
        path = tmp_path / "lineage.jsonl"
        row = evolve.step(path=path, evaluate_fn=fitness_prefers_long_memory)
        assert row["generation"] == 1
        held = evolve.current_genome(path)
        assert held == row["settings"]
        # The fake fitness wants long memory; the winner should have moved
        # that way relative to the seed.
        assert held["half_life_days"] > evolve.SEED["half_life_days"]

    def test_the_lineage_is_append_only(self, tmp_path):
        path = tmp_path / "lineage.jsonl"
        evolve.step(path=path, evaluate_fn=fitness_prefers_long_memory)
        first = path.read_text().splitlines()[0]
        evolve.step(path=path, evaluate_fn=fitness_prefers_long_memory)
        lines = path.read_text().splitlines()
        assert len(lines) == 2
        assert lines[0] == first

    def test_the_champion_defends_and_the_rivals_are_in_the_pool(self, tmp_path):
        path = tmp_path / "lineage.jsonl"
        row = evolve.step(path=path, evaluate_fn=fitness_prefers_long_memory)
        origins = {c["origin"] for c in row["population"]}
        assert "champion" in origins
        assert any(o.startswith("rival:") for o in origins)
        assert any(o == "mutant" or o == "crossover" for o in origins)

    def test_the_same_generation_breeds_the_same_candidates(self, tmp_path):
        a = evolve.step(path=tmp_path / "a.jsonl", evaluate_fn=fitness_prefers_long_memory)
        b = evolve.step(path=tmp_path / "b.jsonl", evaluate_fn=fitness_prefers_long_memory)
        assert json.dumps(a["population"], sort_keys=True) == json.dumps(
            b["population"], sort_keys=True
        )

    def test_a_candidate_that_cannot_be_scored_never_wins(self, tmp_path):
        def flaky(genome, **_):
            return None if genome is not evolve.SEED else 0.0

        row = evolve.step(path=tmp_path / "lineage.jsonl", evaluate_fn=flaky)
        assert row["settings"] == evolve.clamp(evolve.SEED)
