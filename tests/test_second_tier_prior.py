"""Putting a Championship club on the Premier League's scale, for a cup tie.

`team_prior` already does this for a club that has just been PROMOTED. A cup
tie needs the same inference for a club that has not: Wrexham are still in the
Championship and are about to play Arsenal, and something has to say how many
fouls they are likely to give away in that game.

It is the same measurement, so it is the same maths and the same fitted beta.
Only the gate differs: `team_prior` refuses anyone not in this season's
promoted list, and here that gate is exactly the thing being removed.

The rule this must never break is the one promotion.py was written for. Do not
carry the club's LEVEL across. Carrying the level scores 16% worse than using
the league average, despite the two divisions' means differing by almost
nothing. Only the shrunk deviation travels.
"""

from foulgorithm.features import promotion


class TestSecondTierPrior:
    def test_a_championship_club_lands_on_the_premier_league_scale(self):
        prior = promotion.second_tier_prior("Wrexham")
        assert prior is not None
        # Somewhere sane for a top-flight side, not a Championship raw rate.
        assert 8.0 < prior < 14.0

    def test_the_deviation_is_shrunk_not_carried(self):
        # The whole point. A club well above its division average must land
        # much closer to the Premier League mean than its raw rate implies.
        beta = promotion.tier_discount().beta
        assert 0.0 < beta < 0.6

    def test_a_club_above_its_division_lands_above_the_league_mean(self):
        mean = promotion.league_mean()
        rates = promotion._team_fouls(
            promotion._previous(promotion.current_season()), promotion.CHAMPIONSHIP
        )
        hottest = max(rates, key=rates.get)
        prior = promotion.second_tier_prior(hottest)
        assert prior is not None and prior > mean

    def test_a_club_below_its_division_lands_below_the_league_mean(self):
        mean = promotion.league_mean()
        rates = promotion._team_fouls(
            promotion._previous(promotion.current_season()), promotion.CHAMPIONSHIP
        )
        coolest = min(rates, key=rates.get)
        prior = promotion.second_tier_prior(coolest)
        assert prior is not None and prior < mean

    def test_it_never_carries_the_raw_championship_rate(self):
        rates = promotion._team_fouls(
            promotion._previous(promotion.current_season()), promotion.CHAMPIONSHIP
        )
        hottest = max(rates, key=rates.get)
        assert promotion.second_tier_prior(hottest) < rates[hottest]

    def test_a_club_with_no_second_tier_record_is_none(self):
        assert promotion.second_tier_prior("Arsenal") is None

    def test_a_club_we_have_never_heard_of_is_none(self):
        assert promotion.second_tier_prior("Salford") is None

    def test_the_drawn_market_works_the_same_way(self):
        prior = promotion.second_tier_prior("Wrexham", kind=promotion.DRAWN)
        assert prior is not None and 8.0 < prior < 14.0
