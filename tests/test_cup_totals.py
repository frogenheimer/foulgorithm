"""The one model number a cross-division cup tie is allowed to publish.

A Premier League club against a Championship one cannot carry player picks: no
player-level foul data exists for the second tier at any price. A match TOTAL
is different. Total fouls is a team quantity, football-data covers both
divisions back to 2001, and the bridge between them was measured here years
ago as beta 0.373 over 66 promotions.

The failure this model must not have is the one the project was built to avoid.
`match_features._team_rate` returns the league average for a club with no rows,
so an unadjusted model would hand Wrexham exactly average Premier League
behaviour and present that as a read on Wrexham. Silently average is the
mistake. Their second-tier record is shrunk onto the top-flight scale instead,
and where even that is missing the model says so out loud.
"""

import pandas as pd
import pytest

from foulgorithm.features import match_features as mf
from foulgorithm.models import cup_totals


def history(n=400):
    """A synthetic Premier League history: Arsenal quiet, Chelsea busy."""
    rows = []
    base = pd.Timestamp("2024-01-01", tz="UTC")
    clubs = ["Arsenal", "Chelsea", "Leeds", "Everton"]
    fouls = {"Arsenal": 8.0, "Chelsea": 14.0, "Leeds": 11.0, "Everton": 11.0}
    for i in range(n):
        h = clubs[i % 4]
        a = clubs[(i // 4 + 1) % 4]
        if h == a:
            continue
        kickoff = base + pd.Timedelta(days=i)
        rows.append(
            {
                "home_team_raw": h,
                "away_team_raw": a,
                "home_fouls": fouls[h],
                "away_fouls": fouls[a],
                "total_fouls": fouls[h] + fouls[a],
                "kickoff_utc": kickoff,
                "known_at": kickoff,
                "referee_raw": "A Kitchen",
                "odds_home": None,
                "odds_draw": None,
                "odds_away": None,
            }
        )
    return pd.DataFrame(rows)


def tie(home, away, kickoff="2026-01-10"):
    return pd.DataFrame(
        [
            {
                "home_team_raw": home,
                "away_team_raw": away,
                "kickoff_utc": pd.Timestamp(kickoff, tz="UTC"),
                "referee_raw": "A Kitchen",
                "odds_home": None,
                "odds_draw": None,
                "odds_away": None,
            }
        ]
    )


class FixedPriors:
    """Stands in for features.promotion, which reads twenty-six seasons."""

    def __init__(self, committed, drawn=None):
        self.committed = committed
        self.drawn = drawn or committed

    def second_tier_prior(self, club, season=None, kind="committed"):
        table = self.committed if kind == "committed" else self.drawn
        return table.get(club)


class TestAdjustment:
    def test_a_championship_club_does_not_land_on_the_league_average(self):
        # The failure being prevented. Without adjustment _team_rate returns
        # the league mean for a club with no rows, and the tie reads as though
        # we know Wrexham are exactly average, which we do not.
        model = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 13.0}))
        model.fit(history())
        ctx = model.context(tie("Arsenal", "Wrexham").iloc[0])
        assert ctx.away_commit != pytest.approx(1.0)

    def test_a_busier_second_tier_club_raises_its_own_factor(self):
        quiet = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 8.0}))
        busy = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 13.0}))
        for m in (quiet, busy):
            m.fit(history())
        row = tie("Arsenal", "Wrexham").iloc[0]
        assert busy.context(row).away_commit > quiet.context(row).away_commit

    def test_a_premier_league_club_is_left_exactly_as_it_was(self):
        model = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 13.0}))
        model.fit(history())
        row = tie("Arsenal", "Chelsea").iloc[0]
        plain = mf.build_context(
            model._history,
            "Arsenal",
            "Chelsea",
            "A Kitchen",
            row["kickoff_utc"],
            half_life_days=model.half_life_days,
        )
        assert model.context(row).home_commit == pytest.approx(plain.home_commit)

    def test_a_club_with_no_second_tier_record_falls_back_and_is_flagged(self):
        model = cup_totals.CupTotal(priors=FixedPriors({}))
        model.fit(history())
        row = tie("Arsenal", "Wrexham").iloc[0]
        assert model.context(row).away_commit == pytest.approx(1.0)
        assert "Wrexham" in model.unknown(row)

    def test_a_club_we_could_price_is_not_flagged(self):
        model = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 13.0}))
        model.fit(history())
        assert model.unknown(tie("Arsenal", "Wrexham").iloc[0]) == []


class TestPrediction:
    def test_it_returns_a_distribution_per_tie(self):
        model = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 11.0}))
        model.fit(history())
        dists = model.predict(tie("Arsenal", "Wrexham"))
        assert len(dists) == 1
        assert dists[0].mean() > 0

    def test_a_busier_visitor_produces_a_higher_expected_total(self):
        quiet = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 8.0}))
        busy = cup_totals.CupTotal(priors=FixedPriors({"Wrexham": 14.0}))
        for m in (quiet, busy):
            m.fit(history())
        fixture = tie("Arsenal", "Wrexham")
        assert busy.predict(fixture)[0].mean() > quiet.predict(fixture)[0].mean()

    def test_two_premier_league_clubs_match_the_league_model_exactly(self):
        # A cup tie between two top-flight clubs is a league game the model has
        # no reason to treat differently, so it must not.
        from foulgorithm.models.match_models import TeamRatesReferee

        cup = cup_totals.CupTotal(priors=FixedPriors({}))
        league = TeamRatesReferee()
        for m in (cup, league):
            m.fit(history())
        fixture = tie("Arsenal", "Chelsea")
        assert cup.predict(fixture)[0].mean() == pytest.approx(league.predict(fixture)[0].mean())
