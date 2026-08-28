"""The four blocks a cup page renders, built from two team records.

The mirrored-row shape is the league fixture page's, and it is the right one:
a reader compares by looking across a single row rather than by holding a
number in his head while he finds its opposite in a second table.

What is new here is that the two sides may be in different divisions, so every
value carries its OWN division's context. Never a shared one, and never a
number adjusted toward the other side.
"""

from foulgorithm.stats import comparison, team_record
from tests.test_team_record import match


def records(home_rows, away_rows, home="Arsenal", away="Wrexham"):
    return (
        team_record.build(home, home_rows),
        team_record.build(away, away_rows),
    )


HOME = [match("Arsenal", "Chelsea", hf=10, af=12, hy=2, ay=1, hs=15, hc=6, hg=2)]
AWAY = [
    match(
        "Wrexham",
        "Burnley",
        hf=14,
        af=9,
        hy=3,
        ay=2,
        hs=9,
        hc=4,
        hg=1,
        season="2026-27",
        division="E1",
    )
]
BASE = {
    "E0": {"foulsPerMatch": 10.9, "yellowsPerMatch": 1.7, "shotsPerMatch": 12.5},
    "E1": {"foulsPerMatch": 10.8, "yellowsPerMatch": 1.9, "shotsPerMatch": 11.5},
}
RATES = {
    "E0": {"Arsenal": 10.0, "Chelsea": 12.0},
    "E1": {"Wrexham": 14.0, "Burnley": 9.0, "Derby": 11.0},
}


class TestBlocks:
    def test_the_four_blocks_are_present_and_fouls_come_first(self):
        h, a = records(HOME, AWAY)
        blocks = comparison.build(h, a, BASE, RATES)
        assert [b["title"] for b in blocks][:1] == ["Fouls"]
        assert {b["title"] for b in blocks} == {"Fouls", "Cards", "Match shape"}

    def test_every_row_carries_both_sides(self):
        h, a = records(HOME, AWAY)
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["label"] == "Fouls committed per match"
        assert row["home"] == 10.0
        assert row["away"] == 14.0

    def test_the_higher_side_is_marked(self):
        h, a = records(HOME, AWAY)
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["higher"] == "away"

    def test_neither_side_is_marked_when_one_is_missing(self):
        h, a = records(HOME, [])
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["away"] is None
        assert row["higher"] is None


class TestPerSideContext:
    def test_each_side_is_marked_against_its_own_division(self):
        h, a = records(HOME, AWAY)
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert "Premier League" in row["homeNote"]
        assert "Championship" in row["awayNote"]

    def test_the_rank_names_the_division_and_its_size(self):
        h, a = records(HOME, AWAY)
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["awayRank"] == "most in the Championship of 3"

    def test_no_value_gets_no_note(self):
        h, a = records(HOME, [])
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["awayNote"] is None
        assert row["awayRank"] is None


class TestNoAdjustment:
    def test_the_published_value_is_the_raw_one(self):
        # The marker is context. It never changes the number it sits under.
        h, a = records(HOME, AWAY)
        row = comparison.build(h, a, BASE, RATES)[0]["rows"][0]
        assert row["away"] == a.fouls_per_match == 14.0

    def test_no_row_carries_a_cross_division_adjusted_value(self):
        h, a = records(HOME, AWAY)
        for block in comparison.build(h, a, BASE, RATES):
            for row in block["rows"]:
                assert "adjusted" not in row
                assert "normalised" not in row


class TestCrossDivisionWarning:
    def test_a_cross_division_tie_carries_a_warning(self):
        h, a = records(HOME, AWAY)
        note = comparison.cross_division_note(h, a)
        assert note is not None
        assert "Championship" in note and "Premier League" in note

    def test_a_same_division_tie_carries_none(self):
        h, a = records(HOME, [match("Chelsea", "Leeds", hf=11, af=11)], away="Chelsea")
        assert comparison.cross_division_note(h, a) is None
