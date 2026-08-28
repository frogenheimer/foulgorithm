"""Name-keyed joins have now failed twice, so they get a standing guard.

Both failures were silent and both reached published output:

  - `opponent_factor` looked up "Man United" in a history that says "Manchester
    United", found nothing, and returned 1.0. That reads as "perfectly average",
    not as "not found", so roughly half the league lost its adjustment.
  - Settlement recorded "Havertz" and looked for "Kai Havertz". 24 of 1,913
    claims joined, and the 24 were players whose display name happens to equal
    their full name.

The shared fault is not the spelling. It is that a failed lookup returns a
plausible value instead of saying it failed. These tests assert the joins hold
across every spelling we know about, so the next mismatch is loud.
"""

import pytest

from foulgorithm.identity.teams import HISTORY_TO_FIXTURE, history_name


class TestTeamNames:
    def test_every_fixture_spelling_resolves_to_a_history_spelling(self):
        for history, fixture in HISTORY_TO_FIXTURE.items():
            assert history_name(fixture) == history

    def test_resolution_is_idempotent(self):
        # Resolving twice must not walk a name somewhere else. "Coventry" going
        # to "Coventry City" and then somewhere further is how a join that looks
        # fixed breaks again later.
        for fixture in HISTORY_TO_FIXTURE.values():
            once = history_name(fixture)
            assert history_name(once) == once

    def test_an_unknown_club_passes_through_unchanged(self):
        assert history_name("Some New Club") == "Some New Club"


@pytest.mark.network
class TestAgainstRealData:
    def test_every_club_we_predict_exists_in_the_history(self):
        from foulgorithm.identity.teams import from_pulselive
        from foulgorithm.sources import pulselive
        from foulgorithm.store.players import load_player_matches

        known = set(load_player_matches()["opponent"].unique())
        fixtures = pulselive.fixtures()
        if not fixtures:
            pytest.skip("no fixtures published yet")

        unresolved = {
            history_name(from_pulselive(raw)) for f in fixtures for raw in (f.home, f.away)
        } - known

        # A promoted club legitimately has no top-flight history, and that path
        # is handled explicitly. Anything else is a spelling we have not mapped.
        from foulgorithm.features import promotion

        promoted = set(promotion.promoted_clubs(promotion.current_season()))
        promoted |= {history_name(c) for c in promoted}
        assert not (unresolved - promoted), (
            f"clubs we predict but cannot find in the history: {sorted(unresolved - promoted)}. "
            "Add them to HISTORY_TO_FIXTURE rather than letting the join fail silently."
        )
