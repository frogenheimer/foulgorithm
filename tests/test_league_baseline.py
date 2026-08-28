"""Division averages, so a raw number can be read against the right scale.

You asked for raw numbers with a league-average marker, and this is the marker.
It exists because a Championship club on 13.1 fouls a match and a Premier
League club on 13.1 are not saying the same thing. Both get published as they
are, each next to its own division's mean, and the reader does the comparing.

No offset is applied to anything. Adjusting one side toward the other would be
a model judgement inside a section whose whole point is that it is not one.
"""

from foulgorithm.stats import league_baseline as lb
from tests.test_team_record import match


class TestBaseline:
    def test_the_mean_is_over_team_innings_not_matches(self):
        # Every match contributes two team performances, one per side.
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14),
            match("Leeds", "Everton", hf=8, af=12),
        ]
        base = lb.build(rows)
        assert base["foulsPerMatch"] == 11.0
        assert base["matches"] == 2

    def test_fouls_won_averages_to_the_same_number_as_fouls_committed(self):
        # A tautology at league level, and worth pinning: every foul won by one
        # club is a foul committed by another, so the two means must agree.
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14),
            match("Leeds", "Everton", hf=8, af=12),
        ]
        base = lb.build(rows)
        assert base["foulsWonPerMatch"] == base["foulsPerMatch"]

    def test_an_empty_division_has_no_baseline(self):
        assert lb.build([]) == {}


class TestDelta:
    def test_above_average_reads_positive(self):
        assert lb.delta(13.1, {"foulsPerMatch": 11.7}, "foulsPerMatch") == 1.4

    def test_below_average_reads_negative(self):
        assert lb.delta(10.3, {"foulsPerMatch": 11.7}, "foulsPerMatch") == -1.4

    def test_a_missing_value_has_no_delta(self):
        assert lb.delta(None, {"foulsPerMatch": 11.7}, "foulsPerMatch") is None

    def test_a_missing_baseline_has_no_delta(self):
        assert lb.delta(13.1, {}, "foulsPerMatch") is None


class TestMarker:
    def test_the_marker_names_the_division_it_compares_against(self):
        # The division has to be in the words. "+1.4" alone invites exactly the
        # cross-league comparison the marker exists to prevent.
        assert lb.marker(13.1, {"foulsPerMatch": 11.7}, "foulsPerMatch", "E1") == (
            "+1.4 v Championship"
        )

    def test_a_club_on_its_division_average_says_so(self):
        assert lb.marker(11.7, {"foulsPerMatch": 11.7}, "foulsPerMatch", "E0") == (
            "level with Premier League"
        )

    def test_below_average_carries_its_sign(self):
        assert lb.marker(10.3, {"foulsPerMatch": 11.7}, "foulsPerMatch", "E0") == (
            "-1.4 v Premier League"
        )

    def test_nothing_to_compare_gives_no_marker(self):
        assert lb.marker(None, {}, "foulsPerMatch", "E0") is None


class TestRank:
    """Rank, because the two divisions differ in SPREAD more than in level.

    Measured over this window: the Premier League averages 10.75 fouls a match
    and the Championship 10.81, which is nothing. But the Championship spread
    is 40% wider, sd 0.98 against 0.70. So "+1.4" means something different in
    each division, and a delta alone quietly invites the comparison it exists
    to prevent. A rank does not: 3rd of 24 is 3rd of 24 in any league.
    """

    RATES = {"Arsenal": 10.3, "Chelsea": 12.2, "Leeds": 9.7, "Everton": 11.1}

    def test_the_highest_rate_ranks_first(self):
        assert lb.rank(12.2, self.RATES) == (1, 4)

    def test_the_lowest_rate_ranks_last(self):
        assert lb.rank(9.7, self.RATES) == (4, 4)

    def test_a_club_not_in_the_table_still_ranks_against_it(self):
        # A relegated club being compared against its old division.
        assert lb.rank(11.5, self.RATES) == (2, 5)

    def test_no_value_has_no_rank(self):
        assert lb.rank(None, self.RATES) is None

    def test_an_empty_table_has_no_rank(self):
        assert lb.rank(10.3, {}) is None


class TestRankLabel:
    def test_it_reads_as_english_with_the_division_named(self):
        assert lb.rank_label((3, 24), "E1") == "3rd most in the Championship of 24"

    def test_first_and_second_get_their_own_suffixes(self):
        assert lb.rank_label((1, 20), "E0") == "most in the Premier League of 20"
        assert lb.rank_label((2, 20), "E0") == "2nd most in the Premier League of 20"

    def test_last_is_named_as_fewest_rather_than_a_long_ordinal(self):
        assert lb.rank_label((20, 20), "E0") == "fewest in the Premier League of 20"

    def test_the_teens_do_not_get_st_nd_rd(self):
        assert lb.rank_label((11, 24), "E1") == "11th most in the Championship of 24"
        assert lb.rank_label((13, 24), "E1") == "13th most in the Championship of 24"

    def test_no_rank_gives_no_label(self):
        assert lb.rank_label(None, "E0") is None
