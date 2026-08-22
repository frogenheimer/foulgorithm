"""Referee numbers, and the honest limits on reading them.

A referee's fouls per match is not a referee effect. One assigned more derbies
shows more of everything without being any stricter, and separating the two
needs a model with team effects in it. These are observations, and the site says
so wherever they appear.

Cards per FOUL is the more useful column and is here for that reason. Cards per
match rises with how physical the game was; cards per foul asks how likely a
referee is to book an offence he has already given, which is much closer to the
thing people mean by strict.
"""

import pytest

from foulgorithm.publish import site_export


def _match(ref, hf, af, hy, ay, hr=0, ar=0):
    return {
        "referee_raw": ref,
        "home_fouls": hf,
        "away_fouls": af,
        "home_yellows": hy,
        "away_yellows": ay,
        "home_reds": hr,
        "away_reds": ar,
    }


class TestRefereeRows:
    def test_a_referee_under_the_minimum_is_left_out(self):
        rows = site_export._referees([_match("A Smith", 10, 10, 2, 2)], minimum=20)
        assert rows == []

    def test_cards_per_foul_is_independent_of_how_physical_the_game_was(self):
        # Two referees booking one offence in ten. One works scrappier matches.
        # Cards per match separates them; cards per foul should not.
        calm = [_match("Calm", 5, 5, 1, 0) for _ in range(20)]
        scrappy = [_match("Scrappy", 10, 10, 2, 0) for _ in range(20)]
        rows = {r["referee"]: r for r in site_export._referees(calm + scrappy, minimum=20)}
        assert rows["Scrappy"]["cardsPerMatch"] > rows["Calm"]["cardsPerMatch"]
        assert rows["Scrappy"]["cardsPerFoul"] == pytest.approx(
            rows["Calm"]["cardsPerFoul"], abs=1e-6
        )

    def test_reds_are_reported(self):
        rows = site_export._referees(
            [_match("R Strict", 10, 10, 2, 2, 1, 0) for _ in range(20)], minimum=20
        )
        assert rows[0]["redsPerMatch"] == 1.0

    def test_missing_card_counts_do_not_crash_the_row(self):
        # Older season files carry results without cards. A referee whose games
        # are all like that should report no card figure rather than zero, which
        # would read as "never books anyone".
        blank = [
            {**_match("O Ldtimer", 10, 10, 0, 0), "home_yellows": None, "away_yellows": None}
            for _ in range(20)
        ]
        row = site_export._referees(blank, minimum=20)[0]
        assert row["cardsPerMatch"] is None
        assert row["cardsPerFoul"] is None
