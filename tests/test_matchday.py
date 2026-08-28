"""The stats sheet: what happened, with no model anywhere near it.

Built for the reader who wants to be handed the numbers and reach their own
conclusion, rather than be told what to back. Every figure here is an average or
a count from history. Nothing on this page is predicted, which is the point of
it, and the tests exist to keep it that way.

Hit rates are the interesting device. "Over 15.5 fouls, four of the last five"
is a fact a reader can check, unlike a probability, which they can only take on
trust. It carries recent form without pretending to forecast anything.
"""

import pytest

from foulgorithm.publish import matchday


class TestHitRates:
    def test_a_hit_is_strictly_over_the_line(self):
        # Half-lines exist precisely so there is never a push to adjudicate.
        assert matchday.hits([16, 15, 20], 15.5) == [True, False, True]

    def test_most_recent_first(self):
        # Reading order. A row of dots is read left to right as "last match,
        # the one before", so the newest has to lead.
        r = matchday.hit_rate([10, 20, 30], 15.5, window=3)
        assert r["hits"][0] is True, "30 is the most recent value"
        assert r["hits"][-1] is False

    def test_it_reports_how_many_it_had(self):
        # Five dots drawn from three matches would overstate the evidence.
        r = matchday.hit_rate([20, 20], 15.5, window=5)
        assert r["n"] == 2
        assert len(r["hits"]) == 2

    def test_no_history_is_empty_not_zero(self):
        # An empty run of dots reads as "never happened", which is a claim.
        r = matchday.hit_rate([], 15.5, window=5)
        assert r["hits"] == []
        assert r["n"] == 0
        assert r["rate"] is None


class TestLines:
    def test_lines_sit_near_the_middle_of_the_data(self):
        # A line nothing ever clears, or always clears, makes five identical
        # dots and tells the reader nothing.
        assert matchday.line_for([8, 10, 12, 14, 16]) == 11.5

    def test_lines_are_always_half_values(self):
        for values in ([1, 2, 3], [10, 11], [4, 4, 4, 9]):
            assert matchday.line_for(values) % 1 == 0.5

    def test_an_empty_series_has_no_line(self):
        assert matchday.line_for([]) is None


@pytest.mark.network
class TestBuild:
    def test_it_builds_a_fixture_for_every_game(self):
        out = matchday.build()
        assert out["fixtures"], "no fixtures produced"
        for f in out["fixtures"]:
            assert f["home"] and f["away"]
            assert set(f["teams"]) == {f["home"], f["away"]}

    def test_both_sides_carry_the_same_rows(self):
        # The layout is mirrored. A stat present for one side and missing for
        # the other would silently misalign the two columns.
        for f in matchday.build()["fixtures"]:
            home, away = (f["teams"][f[side]] for side in ("home", "away"))
            assert list(home["averages"]) == list(away["averages"])

    def test_the_referee_is_named_or_honestly_absent(self):
        for f in matchday.build()["fixtures"]:
            ref = f["referee"]
            assert ref["name"] is None or isinstance(ref["name"], str)
            if ref["name"] and ref["matches"]:
                assert ref["foulsPerMatch"] is not None

    def test_nothing_here_is_a_prediction(self):
        # A guard, not a formality. The value of this page is that a reader can
        # check every number against a scoreboard.
        import json

        blob = json.dumps(matchday.build())
        for word in ("probability", "expected", "fair", "predict", "model"):
            assert word not in blob.lower(), f"{word!r} leaked onto the stats sheet"


class TestRefereeContext:
    """The referee facts a reader acts on, folded into the sheet: how he
    compares with the league, and what share of fouls he books. The old
    standalone referees page called fouls-booked the only column worth
    reading, then made the reader visit a second page for it."""

    @staticmethod
    def frame():
        import pandas as pd

        return pd.DataFrame(
            [
                # Oliver's two matches run hot: 30 fouls a game, 6 cards.
                {
                    "referee_raw": "Oliver",
                    "home_fouls": 16,
                    "away_fouls": 14,
                    "home_yellows": 3,
                    "away_yellows": 2,
                    "home_reds": 1,
                    "away_reds": 0,
                },
                {
                    "referee_raw": "Oliver",
                    "home_fouls": 15,
                    "away_fouls": 15,
                    "home_yellows": 3,
                    "away_yellows": 3,
                    "home_reds": 0,
                    "away_reds": 0,
                },
                # The rest of the league sits at 20.
                {
                    "referee_raw": "Kavanagh",
                    "home_fouls": 10,
                    "away_fouls": 10,
                    "home_yellows": 1,
                    "away_yellows": 1,
                    "home_reds": 0,
                    "away_reds": 0,
                },
                {
                    "referee_raw": "Kavanagh",
                    "home_fouls": 10,
                    "away_fouls": 10,
                    "home_yellows": 1,
                    "away_yellows": 0,
                    "home_reds": 0,
                    "away_reds": 0,
                },
            ]
        )

    def test_vs_league_and_fouls_booked(self):
        block = matchday._referee_block("Oliver", self.frame())
        # 30 against a league average of 25 is +20%.
        assert block["foulsVsLeague"] == 20
        # 6 cards across 30 fouls books 20% of them.
        assert block["foulsBooked"] == 20

    def test_an_unappointed_referee_carries_the_keys_empty(self):
        block = matchday._referee_block(None, self.frame())
        assert block["foulsVsLeague"] is None
        assert block["foulsBooked"] is None


class TestLeagueRanks:
    """Rank context beside each club average: '3 of 20' where the reader is
    already looking, instead of a separate teams page visit."""

    @staticmethod
    def frame():
        import pandas as pd

        rows = []
        for i, (home, away, hf, af) in enumerate(
            [("A", "B", 16, 8), ("B", "C", 9, 12), ("C", "A", 11, 15)]
        ):
            rows.append(
                {
                    "home_team_raw": home,
                    "away_team_raw": away,
                    "kickoff_utc": f"2026-08-0{i + 1}",
                    "home_fouls": hf,
                    "away_fouls": af,
                    "home_yellows": 1,
                    "away_yellows": 1,
                    "home_reds": 0,
                    "away_reds": 0,
                    "home_shots": 10,
                    "away_shots": 10,
                    "home_corners": 5,
                    "away_corners": 5,
                }
            )
        return pd.DataFrame(rows)

    def test_the_most_fouling_club_ranks_first(self):
        ranks = matchday._league_ranks(self.frame())
        # A commits 15.5 a match, B 8.5, C 11.5.
        assert ranks["clubs"] == 3
        assert ranks["byMetric"]["foulsFor"]["A"] == 1
        assert ranks["byMetric"]["foulsFor"]["B"] == 3

    def test_the_rank_lands_on_the_team_block(self):
        frame = self.frame()
        block = matchday._team_block(frame, "A", ranks=matchday._league_ranks(frame))
        assert block["averages"]["foulsFor"]["rank"] == 1
        assert block["averages"]["foulsFor"]["rankOf"] == 3

    def test_relegated_clubs_do_not_pad_the_field(self):
        """The window spans two seasons, so relegated clubs have rows; the
        rank field is restricted to the current league's clubs."""
        ranks = matchday._league_ranks(self.frame(), clubs=["A", "B"])
        assert ranks["clubs"] == 2
        assert "C" not in ranks["byMetric"]["foulsFor"]
        assert ranks["byMetric"]["foulsFor"]["A"] == 1
