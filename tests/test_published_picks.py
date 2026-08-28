"""The picks we actually showed, kept so they can be marked right or wrong.

The three options on a fixture card are regenerated every publish, so nothing
recorded what a card said at any given moment. Once a game is played there is
no way to show whether the call came in, which is the cheapest and most useful
feedback the site could offer.

Versioned rather than write-once, because a midweek model change SHOULD produce
different picks and pretending otherwise would be dishonest. Every version is
kept; the last one published before kickoff is the one that counts, because that
is what a reader saw when the game started.
"""

from foulgorithm.store import published_picks as store


def option(band="Short", odds=3.0, legs=(("Guiu", 2),)):
    return {
        "band": band,
        "character": "alan",
        "odds": odds,
        "outOf100": round(100 / odds),
        "totalFouls": sum(f for _, f in legs),
        "legs": [{"player": p, "fouls": f, "market": "committed", "outOf100": 40} for p, f in legs],
    }


KICKOFF = "2026-08-24T19:00:00+00:00"


class TestVersioning:
    def test_the_first_publish_is_version_one(self, tmp_path):
        store.record("Fulham v Chelsea", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path)
        versions = store.versions("Fulham v Chelsea", tmp_path)
        assert len(versions) == 1 and versions[0]["version"] == 1

    def test_republishing_the_same_picks_does_not_add_a_version(self, tmp_path):
        for _ in range(3):
            store.record(
                "Fulham v Chelsea", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path
            )
        assert len(store.versions("Fulham v Chelsea", tmp_path)) == 1

    def test_changed_picks_add_a_version(self, tmp_path):
        store.record("Fulham v Chelsea", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path)
        store.record(
            "Fulham v Chelsea",
            KICKOFF,
            [option(legs=(("Mudryk", 2),))],
            "2026-08-23T10:00:00+00:00",
            tmp_path,
        )
        versions = store.versions("Fulham v Chelsea", tmp_path)
        assert [v["version"] for v in versions] == [1, 2]

    def test_earlier_versions_are_never_overwritten(self, tmp_path):
        store.record("Fulham v Chelsea", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path)
        store.record(
            "Fulham v Chelsea",
            KICKOFF,
            [option(legs=(("Mudryk", 2),))],
            "2026-08-23T10:00:00+00:00",
            tmp_path,
        )
        first = store.versions("Fulham v Chelsea", tmp_path)[0]
        assert first["options"][0]["legs"][0]["player"] == "Guiu"


class TestWhatCounts:
    def test_the_last_version_before_kickoff_is_the_one_scored(self, tmp_path):
        store.record("F v C", KICKOFF, [option(odds=2.0)], "2026-08-22T10:00:00+00:00", tmp_path)
        store.record("F v C", KICKOFF, [option(odds=5.0)], "2026-08-24T18:00:00+00:00", tmp_path)
        final = store.final("F v C", tmp_path)
        assert final["options"][0]["odds"] == 5.0

    def test_a_version_published_after_kickoff_never_counts(self, tmp_path):
        """Otherwise a rerun after the whistle rewrites what we called."""
        store.record("F v C", KICKOFF, [option(odds=2.0)], "2026-08-22T10:00:00+00:00", tmp_path)
        store.record("F v C", KICKOFF, [option(odds=9.0)], "2026-08-24T21:00:00+00:00", tmp_path)
        assert store.final("F v C", tmp_path)["options"][0]["odds"] == 2.0

    def test_nothing_published_before_kickoff_scores_nothing(self, tmp_path):
        store.record("F v C", KICKOFF, [option()], "2026-08-25T10:00:00+00:00", tmp_path)
        assert store.final("F v C", tmp_path) is None

    def test_an_unknown_fixture_has_no_final(self, tmp_path):
        assert store.final("Nobody v Nobody", tmp_path) is None


class TestSafety:
    def test_no_options_records_nothing(self, tmp_path):
        store.record("F v C", KICKOFF, [], "2026-08-22T10:00:00+00:00", tmp_path)
        assert store.versions("F v C", tmp_path) == []

    def test_fixtures_do_not_collide(self, tmp_path):
        store.record("A v B", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path)
        store.record("C v D", KICKOFF, [option()], "2026-08-22T10:00:00+00:00", tmp_path)
        assert len(store.versions("A v B", tmp_path)) == 1
        assert len(store.versions("C v D", tmp_path)) == 1


class TestScoringACard:
    """A leg is green when it landed, red when it did not, and neither until the
    outcome exists. An unsettled leg shown as red would read as a loss we have
    not had."""

    OUTCOMES = {("Guiu", "committed", 1.5): True, ("Mudryk", "committed", 1.5): False}

    def test_a_landed_leg_is_marked_landed(self):
        scored = store.score(option(legs=(("Guiu", 2),)), self.OUTCOMES)
        assert scored["legs"][0]["landed"] is True

    def test_a_missed_leg_is_marked_missed(self):
        scored = store.score(option(legs=(("Mudryk", 2),)), self.OUTCOMES)
        assert scored["legs"][0]["landed"] is False

    def test_an_unsettled_leg_is_marked_neither(self):
        scored = store.score(option(legs=(("Nobody", 2),)), self.OUTCOMES)
        assert scored["legs"][0]["landed"] is None

    def test_a_card_lands_only_when_every_leg_does(self):
        both = store.score(option(legs=(("Guiu", 2), ("Mudryk", 2))), self.OUTCOMES)
        assert both["landed"] is False

        one = store.score(option(legs=(("Guiu", 2),)), self.OUTCOMES)
        assert one["landed"] is True

    def test_a_part_settled_card_is_undecided(self):
        mixed = store.score(option(legs=(("Guiu", 2), ("Nobody", 2))), self.OUTCOMES)
        assert mixed["landed"] is None, "half settled is not half lost"

    def test_a_card_already_lost_is_lost_even_if_the_rest_is_unsettled(self):
        """One miss settles a combination. Waiting on the others changes nothing."""
        mixed = store.score(option(legs=(("Mudryk", 2), ("Nobody", 2))), self.OUTCOMES)
        assert mixed["landed"] is False
