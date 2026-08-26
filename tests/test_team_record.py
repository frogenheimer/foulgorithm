"""A club's raw record, measured identically in both divisions.

The cup pages compare a Premier League club with a Championship one, and the
only way that is honest is if both sides come from one source measured one
way. That source is football-data.co.uk, which carries six team stats a match
and the referee for E0 and E1 alike.

Two things this module must get right. A club that changed division inside the
window keeps its spells separate, so the page can say "38 in the Championship,
8 in the Premier League" rather than silently pooling two different games. And
fouls WON is the opponent's fouls committed, which is the only place that
number exists at team level.
"""

import pytest

from foulgorithm.stats import team_record as tr


def match(home, away, *, hf, af, hy=0, ay=0, hr=0, ar=0, hs=0, ashots=0,
          hst=0, ast=0, hc=0, ac=0, hg=0, ag=0, ref="A Kitchen", season="2026-27",
          division="E0"):
    return {
        "home_team_raw": home, "away_team_raw": away,
        "home_fouls": hf, "away_fouls": af,
        "home_yellows": hy, "away_yellows": ay,
        "home_reds": hr, "away_reds": ar,
        "home_shots": hs, "away_shots": ashots,
        "home_shots_on_target": hst, "away_shots_on_target": ast,
        "home_corners": hc, "away_corners": ac,
        "home_goals": hg, "away_goals": ag,
        "referee_raw": ref, "season": season, "division": division,
    }


class TestFoulCore:
    def test_fouls_committed_averages_both_venues(self):
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14),
            match("Chelsea", "Arsenal", hf=12, af=16),
        ]
        rec = tr.build("Arsenal", rows)
        assert rec.matches == 2
        assert rec.fouls_per_match == 13.0      # 10 home, 16 away

    def test_fouls_won_is_the_opponents_fouls_committed(self):
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14),
            match("Chelsea", "Arsenal", hf=12, af=16),
        ]
        rec = tr.build("Arsenal", rows)
        assert rec.fouls_won_per_match == 13.0  # 14 conceded to them, then 12

    def test_home_and_away_fouls_split(self):
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14),
            match("Chelsea", "Arsenal", hf=12, af=16),
        ]
        rec = tr.build("Arsenal", rows)
        assert rec.fouls_home == 10.0
        assert rec.fouls_away == 16.0

    def test_a_club_that_never_played_at_home_has_no_home_figure(self):
        rec = tr.build("Arsenal", [match("Chelsea", "Arsenal", hf=12, af=16)])
        assert rec.fouls_home is None
        assert rec.fouls_away == 16.0


class TestCards:
    def test_cards_per_foul_is_the_readable_one(self):
        # Matching publish/site_export: cards per match rises with how physical
        # the game was, cards per foul asks how often an offence gets booked.
        rows = [match("Arsenal", "Chelsea", hf=10, af=14, hy=2, ay=3)]
        rec = tr.build("Arsenal", rows)
        assert rec.yellows_per_match == 2.0
        assert rec.cards_per_foul == pytest.approx(0.2)

    def test_a_missing_card_column_is_excluded_not_counted_as_zero(self):
        # Old season files carry results without cards. Folding those in as
        # zero reads as "never booked", which is a claim we cannot make.
        rows = [
            match("Arsenal", "Chelsea", hf=10, af=14, hy=2, ay=1),
            {**match("Arsenal", "Chelsea", hf=10, af=14), "home_yellows": None, "away_yellows": None},
        ]
        rec = tr.build("Arsenal", rows)
        assert rec.carded_matches == 1
        assert rec.yellows_per_match == 2.0

    def test_no_card_data_at_all_leaves_the_figures_absent(self):
        rows = [{**match("Arsenal", "Chelsea", hf=10, af=14),
                 "home_yellows": None, "away_yellows": None}]
        rec = tr.build("Arsenal", rows)
        assert rec.yellows_per_match is None
        assert rec.cards_per_foul is None


class TestSpells:
    def test_a_club_that_changed_division_keeps_its_spells_apart(self):
        rows = [
            match("Burnley", "Watford", hf=12, af=10, season="2025-26", division="E1"),
            match("Watford", "Burnley", hf=11, af=13, season="2025-26", division="E1"),
            match("Burnley", "Arsenal", hf=9, af=8, season="2026-27", division="E0"),
        ]
        rec = tr.build("Burnley", rows)
        assert rec.matches == 3
        assert [(s.season, s.division, s.matches) for s in rec.spells] == [
            ("2025-26", "E1", 2),
            ("2026-27", "E0", 1),
        ]

    def test_the_spell_label_reads_as_english(self):
        rows = [
            match("Burnley", "Watford", hf=12, af=10, season="2025-26", division="E1"),
            match("Watford", "Burnley", hf=11, af=13, season="2025-26", division="E1"),
            match("Burnley", "Arsenal", hf=9, af=8, season="2026-27", division="E0"),
        ]
        rec = tr.build("Burnley", rows)
        assert rec.spell_label() == "2 in the Championship, 1 in the Premier League"

    def test_a_club_that_never_moved_says_so_plainly(self):
        rows = [match("Arsenal", "Chelsea", hf=10, af=14)]
        rec = tr.build("Arsenal", rows)
        assert rec.spell_label() == "1 in the Premier League"

    def test_the_pooled_rate_spans_both_divisions(self):
        # Pool, and label the split. Never pool silently.
        rows = [
            match("Burnley", "Watford", hf=12, af=10, season="2025-26", division="E1"),
            match("Burnley", "Arsenal", hf=8, af=8, season="2026-27", division="E0"),
        ]
        rec = tr.build("Burnley", rows)
        assert rec.fouls_per_match == 10.0
        assert rec.crossed_divisions is True


class TestMatchShape:
    def test_shots_corners_and_goals_come_through(self):
        rows = [match("Arsenal", "Chelsea", hf=10, af=14, hs=15, ashots=7,
                      hst=6, ast=2, hc=8, ac=3, hg=3, ag=1)]
        rec = tr.build("Arsenal", rows)
        assert rec.shots_per_match == 15.0
        assert rec.shots_on_target_per_match == 6.0
        assert rec.corners_per_match == 8.0
        assert rec.goals_for_per_match == 3.0
        assert rec.goals_against_per_match == 1.0


class TestEmptiness:
    def test_a_club_with_no_matches_is_empty_not_zero(self):
        # Zero fouls per match is a claim. No matches is an absence.
        rec = tr.build("Arsenal", [])
        assert rec.matches == 0
        assert rec.fouls_per_match is None
        assert rec.spells == ()
