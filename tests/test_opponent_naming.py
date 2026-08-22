"""The opponent factor was silently disabled for half the league.

Fixtures spell a club "Man United". The player history spells it "Manchester
United". `opponent_factor` looked the name up in the history, found nothing and
returned 1.0, which reads as "this opponent is perfectly average" rather than as
"I could not find this opponent".

It was not a small effect being lost. Manchester United's real factor is 0.84
and Tottenham's is 1.25, so roughly a fifth of the adjustment was being thrown
away for around half the clubs, in published output.

This is the failure mode the no-name-keyed-joins rule exists to prevent, and it
got in anyway, so it gets a test of its own.
"""

import pandas as pd
import pytest

from foulgorithm.models import player_models as pm
from foulgorithm.store.players import load_player_matches

AS_OF = pd.Timestamp("2026-08-20", tz="UTC")


@pytest.fixture(scope="module")
def model():
    m = pm.build("valentina", "player_fouls_committed")
    m.fit(load_player_matches())
    return m


@pytest.mark.network
@pytest.mark.parametrize(
    "fixture_name,history_name",
    [
        ("Man United", "Manchester United"),
        ("Man City", "Manchester City"),
        ("Tottenham", "Tottenham Hotspur"),
        ("Newcastle", "Newcastle United"),
        ("Nott'm Forest", "Nottingham Forest"),
        ("Brighton", "Brighton & Hove Albion"),
    ],
)
def test_both_spellings_give_the_same_factor(model, fixture_name, history_name):
    assert model.opponent_factor(fixture_name, AS_OF) == pytest.approx(
        model.opponent_factor(history_name, AS_OF), abs=1e-9
    )


@pytest.mark.network
def test_an_established_club_is_not_silently_average(model):
    # 1.0 exactly is the signature of the bug: a real ratio landing on exactly
    # one is possible but not for six clubs at once.
    factors = [
        model.opponent_factor(n, AS_OF)
        for n in ("Man United", "Man City", "Tottenham", "Newcastle", "Arsenal", "Chelsea")
    ]
    assert sum(f == 1.0 for f in factors) == 0
