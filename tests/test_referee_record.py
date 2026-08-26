"""What we can honestly say about the official, and what we cannot.

Carried straight from publish/site_export and tests/test_referees: a
referee's fouls per match is NOT a referee effect. One handed more derbies
shows more of everything without being any stricter. Cards per foul is the
column worth reading, because it asks how likely he is to book an offence he
has already given.

These are observations. The cup page says so, and none of this reaches a model.
"""

import pytest

from foulgorithm.stats import referee_record as rr
from tests.test_team_record import match


class TestOfficial:
    def test_it_counts_only_this_referees_matches(self):
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=12, ref="A Kitchen"),
            match("Leeds", "Everton", hf=20, af=20, ref="M Oliver"),
        ]
        rec = rr.build("A Kitchen", rows)
        assert rec.matches == 1
        assert rec.fouls_per_match == 22.0

    def test_it_joins_across_the_sources_three_spellings(self):
        rows = [match("Arsenal", "Chelsea", hf=10, af=12, ref="A Kitchen")]
        assert rr.build("Andrew Kitchen, England", rows).matches == 1

    def test_cards_per_foul_is_published(self):
        rows = [match("Arsenal", "Chelsea", hf=10, af=10, hy=2, ay=2)]
        rec = rr.build("A Kitchen", rows)
        assert rec.cards_per_foul == pytest.approx(0.2)

    def test_a_referee_we_have_never_seen_is_empty_not_zero(self):
        rec = rr.build("Z Nobody", [match("Arsenal", "Chelsea", hf=10, af=12)])
        assert rec.matches == 0
        assert rec.fouls_per_match is None

    def test_no_appointed_referee_gives_nothing_rather_than_raising(self):
        assert rr.build(None, [match("Arsenal", "Chelsea", hf=10, af=12)]) is None


class TestUnderThisReferee:
    def test_a_clubs_record_under_the_official_counts_only_their_games(self):
        rows = [
            match("Arsenal", "Chelsea", hf=9, af=12, ref="A Kitchen"),
            match("Leeds", "Arsenal", hf=11, af=15, ref="A Kitchen"),
            match("Arsenal", "Leeds", hf=30, af=30, ref="M Oliver"),
        ]
        rec = rr.build("A Kitchen", rows)
        arsenal = rec.club("Arsenal")
        assert arsenal.matches == 2
        assert arsenal.fouls_per_match == 12.0     # 9 at home, then 15 away

    def test_a_club_that_never_had_him_is_honest_about_it(self):
        rows = [match("Arsenal", "Chelsea", hf=9, af=12, ref="A Kitchen")]
        leeds = rr.build("A Kitchen", rows).club("Leeds")
        assert leeds.matches == 0
        assert leeds.fouls_per_match is None


class TestThinEvidence:
    def test_a_referee_with_few_matches_is_flagged(self):
        # Not hidden. Shown with the count, so the reader discounts it himself.
        rows = [match("Arsenal", "Chelsea", hf=10, af=12)] * 3
        assert rr.build("A Kitchen", rows).thin is True

    def test_a_full_record_is_not_flagged(self):
        rows = [match("Arsenal", "Chelsea", hf=10, af=12)] * 25
        assert rr.build("A Kitchen", rows).thin is False
