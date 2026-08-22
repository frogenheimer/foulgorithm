"""Promoted clubs arrive with no Premier League history, and that is now live.

Coventry and Hull came up for 2026/27. Nine of eleven of their players are
flagged thin, and their team rate is the league average, which is a guess
wearing a number's clothes.

Championship PLAYER data does not exist at any price. FBref's advanced stats
cover the top five European leagues only, so there is no second-tier fouls
table to download. Match-level data does exist, which means the team rate is
recoverable even though the player rates are not.

The discount is measured, not assumed: every club promoted since 2001 has a
final Championship season and a first Premier League season, and the ratio
between the two is the thing we want.
"""

import pytest

from foulgorithm.features import promotion

# Every test here downloads season files. CI must not depend on a third party
# being up, per .github/workflows/test.yml.
pytestmark = pytest.mark.network


class TestDiscount:
    def test_discount_is_a_ratio_not_a_guess(self):
        d = promotion.tier_discount()
        assert d.observations >= 30, "too few promoted clubs to claim anything"
        assert 0.1 < d.beta < 0.7, "a beta outside this range is a bug, not a finding"
        assert d.beta < 0.9, "carrying the level whole is the version that loses"

    def test_it_reports_its_own_uncertainty(self):
        # A ratio without a spread invites treating 0.97 and 0.97 +/- 0.15 the
        # same way. They are not the same.
        d = promotion.tier_discount()
        assert d.spread > 0

    def test_promoted_clubs_are_named_from_data_not_hard_coded(self):
        # The 2025 version hard-coded 20 club names and needed editing every
        # August. Promotion is derivable: in E0 this season, not last.
        promoted = promotion.promoted_clubs("2026-27")
        assert 0 < len(promoted) <= 4
        assert all(isinstance(c, str) and c for c in promoted)


class TestPrior:
    def test_a_promoted_club_gets_its_own_number_not_the_league_average(self):
        league, prior = promotion.league_mean(), promotion.team_prior("Coventry", "2026-27")
        assert prior is not None
        assert prior != pytest.approx(league, abs=0.01), (
            "if a promoted club lands exactly on the league mean, the "
            "Championship data is not reaching the prior"
        )

    def test_an_established_club_has_no_promotion_prior(self):
        assert promotion.team_prior("Arsenal", "2026-27") is None

    def test_an_unknown_club_does_not_raise(self):
        # Halting the pipeline is right for an unresolved identity. A club with
        # no second-tier history is not that: it is a club we simply cannot
        # help, and the caller falls back to the league mean.
        assert promotion.team_prior("Not A Real Club", "2026-27") is None


class TestOpponentFactor:
    def test_a_promoted_club_gets_a_factor_not_a_shrug(self):
        f = promotion.opponent_factor("Coventry", "2026-27")
        assert f is not None
        assert 0.8 < f < 1.2
        assert f != 1.0

    def test_an_established_club_is_left_alone(self):
        assert promotion.opponent_factor("Arsenal", "2026-27") is None
