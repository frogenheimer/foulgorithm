"""Six leagues in one frame, each row knowing which league it came from.

Additive on purpose. `load_player_matches()` is what every model reads and it
still returns England alone, unchanged, because pooling is a modelling decision
that belongs to roadmap item 8 and not to a data-loading change.

The rule this enforces: **no row may lose its league.** Serie A runs 1.197 fouls
per 90 against England's 0.972, a 23% gap, against a 9% spread across England's
own eight seasons. A pooled frame without a league column would overstate every
Italian player by about a fifth, and would do it silently.
"""

from foulgorithm.store import players as store


class TestTheEnglandPathIsUntouched:
    """The models read this. It must keep meaning exactly what it meant."""

    def test_it_still_returns_one_league(self):
        d = store.load_player_matches()
        assert len(d) > 50_000
        if "league" in d.columns:
            assert set(d["league"].unique()) == {"ENG"}

    def test_it_still_has_the_columns_models_expect(self):
        d = store.load_player_matches()
        for column in (
            "player",
            "team",
            "opponent",
            "kickoff_utc",
            "known_at",
            "minutes",
            "fouls_committed",
            "fouls_drawn",
        ):
            assert column in d.columns


class TestPooling:
    def test_every_row_carries_a_league(self):
        d = store.load_all_leagues()
        assert "league" in d.columns
        assert d["league"].notna().all()

    def test_more_than_one_league_is_present(self):
        d = store.load_all_leagues()
        assert len(set(d["league"].unique())) > 1

    def test_it_is_bigger_than_england_alone(self):
        assert len(store.load_all_leagues()) > len(store.load_player_matches())

    def test_the_english_rows_match_the_england_only_frame(self):
        """Pooling must not quietly reshape the league we already had."""
        pooled = store.load_all_leagues()
        english = pooled[pooled["league"] == "ENG"]
        assert len(english) == len(store.load_player_matches())

    def test_the_league_gap_is_real_and_visible(self):
        """The number that makes naive pooling wrong, asserted so it stays true."""
        d = store.load_all_leagues()
        d = d[d["minutes"] > 0]
        rates = {}
        for code in ("ENG", "ITA"):
            side = d[d["league"] == code]
            rates[code] = side["fouls_committed"].sum() / (side["minutes"].sum() / 90)
        assert rates["ITA"] > rates["ENG"] * 1.1, f"Italy should sit well above England: {rates}"

    def test_a_league_we_do_not_hold_is_absent_rather_than_empty_rows(self):
        d = store.load_all_leagues(codes=("ENG",))
        assert set(d["league"].unique()) == {"ENG"}
