"""A promoted club's players priced as that club, not as the league average.

Coventry have a Premier League record for 7 of 31 squad players and Hull for 8
of 31, against Arsenal's 28 of 29. Roughly three quarters of a promoted squad is
invisible, so every one of those players falls back to a position average and
every Coventry defender is priced identically to every other.

We already compute each promoted club's Championship foul rate and already turn
it into a club prior. It was simply never applied to that club's own players.

**This is an estimate and has to look like one.** It says "we have never seen
this player in this division, and his club fouled at this rate in the one below".
That is worth more than the league average and much less than a record, and the
`why` block marks it so the site can say so.
"""

import pandas as pd
import pytest

from foulgorithm.models import player_models as pm


def history(rows):
    return pd.DataFrame(
        [
            {
                "player": n,
                "team": t,
                "opponent": "O",
                "venue": "H",
                "kickoff_utc": pd.Timestamp(d, tz="UTC"),
                "known_at": pd.Timestamp(d, tz="UTC"),
                "season": 2026,
                "position": p,
                "minutes": 90,
                "fouls_committed": f,
                "fouls_drawn": 1,
                "yellows": 0,
                "reds": 0,
                "tackles_won": 1,
                "interceptions": 1,
                "source": "test",
            }
            for n, t, d, p, f in rows
        ]
    )


AS_OF = pd.Timestamp("2026-08-24", tz="UTC")


def fitted():
    """Enough players, each with enough matches, that a position prior exists.

    One appearance each is not enough: the fit needs real playing time per
    position, and a player with a single match is not one whose own record
    should dominate anything.
    """
    rows = []
    for i in range(20):
        for day in range(1, 26):
            rows.append((f"P{i}", "Arsenal", f"2026-01-{day:02d}", "CB", 1))
            rows.append((f"M{i}", "Arsenal", f"2026-01-{day:02d}", "CM", 2))
    model = pm.build("tayler")
    model.fit(history(rows))
    return model


class TestTheClubFactor:
    def test_a_dirtier_promoted_club_lifts_the_prior(self):
        model = fitted()
        plain = model.prior_rate("Nobody")
        lifted = model.prior_rate("Nobody", club_factor=1.2)
        assert lifted == pytest.approx(plain * 1.2)

    def test_a_cleaner_promoted_club_lowers_it(self):
        model = fitted()
        assert model.prior_rate("Nobody", club_factor=0.8) == pytest.approx(
            model.prior_rate("Nobody") * 0.8
        )

    def test_no_factor_changes_nothing(self):
        model = fitted()
        assert model.prior_rate("Nobody", club_factor=None) == model.prior_rate("Nobody")
        assert model.prior_rate("Nobody", club_factor=1.0) == model.prior_rate("Nobody")

    def test_it_scales_the_position_prior_not_the_league_one(self):
        """A defender at a dirty promoted club is still a defender."""
        model = fitted()
        # Read a real position key rather than inventing one: the fit keys on
        # detailed codes (CB, CM, DM), not on DF/MF.
        pos = next(iter(model._position_rate))
        model._player_position["Known"] = pos
        mid = model.prior_rate("Known", club_factor=1.2)
        assert mid == pytest.approx(model._position_rate[pos] * 1.2)


class TestItIsMarkedAsAnEstimate:
    def test_a_player_with_no_record_is_flagged(self):
        model = fitted()
        _, why = model.predict_one("Nobody", "Arsenal", AS_OF, team="Coventry")
        assert why["priorFrom"] == "promoted-club", why

    def test_a_player_with_a_record_is_not_flagged(self):
        model = fitted()
        _, why = model.predict_one("P1", "Arsenal", AS_OF, team="Arsenal")
        assert why["priorFrom"] == "own-record"

    def test_an_established_club_with_no_record_says_position(self):
        model = fitted()
        _, why = model.predict_one("Nobody", "Arsenal", AS_OF, team="Arsenal")
        assert why["priorFrom"] == "position"

    def test_every_prediction_says_where_its_prior_came_from(self):
        """Three states, always one of them. Silence would be the worst option."""
        model = fitted()
        for player, team in (("P1", "Arsenal"), ("Nobody", "Arsenal"), ("Nobody", "Coventry")):
            _, why = model.predict_one(player, "Arsenal", AS_OF, team=team)
            assert why["priorFrom"] in {"own-record", "position", "promoted-club"}


class TestItDoesNotDisturbPlayersWeKnow:
    def test_a_known_player_moves_only_slightly(self):
        """The prior still counts for a known player, and that is the design.

        Tayler shrinks with prior_matches=30, so a player with 25 matches sits
        roughly half on his own record and half on the prior. A club factor of a
        few percent therefore moves him a couple of percent, which is shrinkage
        working rather than the club prior overreaching. Asserting he is
        completely unmoved would be asserting the shrinkage is broken.
        """
        model = fitted()
        a, _ = model.predict_one("P1", "Arsenal", AS_OF, team="Arsenal")
        b, _ = model.predict_one("P1", "Arsenal", AS_OF, team="Coventry")
        move = abs(a.mean() - b.mean()) / a.mean()
        assert move < 0.05, f"moved {move:.1%}, too much for a 25-match record"

    def test_an_unknown_player_moves_more_than_a_known_one(self):
        """The whole point: the less we know, the more the club should matter."""
        model = fitted()
        known_a, _ = model.predict_one("P1", "Arsenal", AS_OF, team="Arsenal")
        known_b, _ = model.predict_one("P1", "Arsenal", AS_OF, team="Coventry")
        new_a, _ = model.predict_one("Nobody", "Arsenal", AS_OF, team="Arsenal")
        new_b, _ = model.predict_one("Nobody", "Arsenal", AS_OF, team="Coventry")

        known_move = abs(known_a.mean() - known_b.mean()) / known_a.mean()
        new_move = abs(new_a.mean() - new_b.mean()) / new_a.mean()
        assert new_move > known_move
