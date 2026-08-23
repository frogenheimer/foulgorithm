"""The combination search, replaced by an exact method rather than a faster guess.

Profiling a publish run found `best_tickets` evaluating a generator 173 million
times: it enumerated every combination of every size and then threw away the
ones that did not hit the target or reused a player. With fourteen players at
three lines each that is C(42, 4) per target per fixture, almost all of it
discarded.

Choosing at most one leg per player to hit an exact foul total while maximising
a product of probabilities is a knapsack, and knapsacks have exact dynamic
programming solutions. This is not an approximation and these tests exist to
prove it: the answer must match the exhaustive search on every case, not merely
come close.
"""

import random

import pytest

from foulgorithm.publish import combinations as combo


def legs(spec):
    return [
        combo.Leg(player=p, team="A", market="committed", line=f - 0.5, prob=q)
        for p, f, q in spec
    ]


def brute_force(all_legs, target, min_legs=combo.MIN_LEGS, max_legs=combo.MAX_LEGS):
    """The original algorithm, kept as the oracle."""
    from itertools import combinations as it_combinations

    best = None
    for size in range(min_legs, max_legs + 1):
        for candidate in it_combinations(all_legs, size):
            if len({leg.player for leg in candidate}) != size:
                continue
            if sum(leg.fouls for leg in candidate) != target:
                continue
            p = 1.0
            for leg in candidate:
                p *= leg.prob
            if best is None or p > best[0]:
                best = (p, candidate)
    return best


class TestItMatchesTheExhaustiveSearch:
    @pytest.mark.parametrize("seed", range(12))
    def test_same_probability_on_random_pools(self, seed):
        rng = random.Random(seed)
        pool = legs(
            [
                (f"P{i}", f, round(rng.uniform(0.08, 0.92), 4))
                for i in range(9)
                for f in (1, 2, 3)
            ]
        )
        for target in (4, 5, 6):
            mine = combo.best_combination(pool, target)
            theirs = brute_force(pool, target)
            if theirs is None:
                assert mine is None
                continue
            assert mine is not None, f"found nothing where the oracle found {theirs[0]}"
            assert mine[0] == pytest.approx(theirs[0], rel=1e-9)

    def test_it_uses_a_player_at_most_once(self):
        pool = legs([("Solo", 1, 0.9), ("Solo", 2, 0.9), ("Solo", 3, 0.9)])
        assert combo.best_combination(pool, 4) is None, "one player cannot fill four"

    def test_it_respects_the_leg_count_bounds(self):
        pool = legs([(f"P{i}", 1, 0.9) for i in range(8)])
        # Six legs of one foul would reach six, but MAX_LEGS is four.
        assert combo.best_combination(pool, 6) is None
        assert combo.best_combination(pool, 4) is not None

    def test_a_single_leg_is_not_a_ticket(self):
        pool = legs([("A", 4, 0.5), ("B", 2, 0.5), ("C", 2, 0.5)])
        chosen = combo.best_combination(pool, 4)
        assert chosen is not None
        assert len(chosen[1]) >= combo.MIN_LEGS

    def test_it_finds_nothing_when_the_target_is_unreachable(self):
        assert combo.best_combination(legs([("A", 1, 0.9), ("B", 1, 0.9)]), 99) is None

    def test_an_empty_pool_is_safe(self):
        assert combo.best_combination([], 4) is None


class TestItIsActuallyFast:
    def test_a_full_fixture_pool_is_not_combinatorial(self):
        """Fourteen players at three lines: the case that took the time."""
        import time

        pool = legs([(f"P{i}", f, 0.4 + (i % 5) * 0.08) for i in range(28) for f in (1, 2, 3)])
        start = time.perf_counter()
        for target in (4, 5, 6):
            combo.best_combination(pool, target)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"took {elapsed:.2f}s, which is the old problem again"
