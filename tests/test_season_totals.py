"""Season totals as dated evidence, never as undated blocks.

The C1 blend from docs/34-final-plan.md: official season totals enter the
empirical-Bayes rate as pseudo-exposure, dated across the part of the season
the archive does not cover, decayed by event date, gated by knowability, and
contributing exactly nothing where the archive is already complete. That last
property is the double-count release gate, and it is tested here as an
equality, not a tolerance.
"""

import numpy as np
import pandas as pd
import pytest

from foulgorithm.features import season_totals as st
from foulgorithm.models.player_models import PlayerFoulModel

UTC = "UTC"

# Unit tests pin the offset to neutral; the real reference file is a
# measurement that can change, and these tests assert arithmetic, not it.
NEUTRAL = {"seasons": {}, "global": {"ratio": 1.0}}


def archive_rows(player, dates, minutes=90.0, fouls=1.0, drawn=0.0, position="DM"):
    stamps = pd.to_datetime(dates, utc=True)
    return pd.DataFrame(
        {
            "player": player,
            "team": "Testchester",
            "opponent": "Rivals",
            "kickoff_utc": stamps,
            "known_at": stamps + pd.Timedelta(hours=3),
            "season": [s.year + 1 if s.month >= 8 else s.year for s in stamps],
            "position": position,
            "minutes": minutes,
            "fouls_committed": fouls,
            "fouls_drawn": drawn,
        }
    )


def api_row(player, season, minutes, fouls, drawn=None, fetched="2026-08-24T00:00:00+00:00"):
    return {
        "player": player,
        "season": season,
        "mins_played": minutes,
        "fouls": fouls,
        "was_fouled": drawn,
        "fetchedAt": fetched,
    }


class TestSeasonWindow:
    def test_a_completed_season_spans_august_to_may(self):
        start, end = st.season_window("2023/24")
        assert start == pd.Timestamp("2023-08-01", tz=UTC)
        assert end == pd.Timestamp("2024-05-31", tz=UTC)

    def test_covid_season_ends_in_july(self):
        _, end = st.season_window("2019/20")
        assert end == pd.Timestamp("2020-07-31", tz=UTC)


class TestBuildingEvidence:
    def test_a_player_with_no_archive_rows_gets_the_whole_season(self):
        api = pd.DataFrame([api_row("Novel Signing", "2023/24", 900.0, 10.0, drawn=5.0)])
        got = st.evidence(api, archive_rows("Someone Else", ["2023-09-02"]), offset=NEUTRAL)
        mine = got[got["player"] == "Novel Signing"]
        assert mine["minutes"].sum() == pytest.approx(900.0)
        assert mine["fouls_committed"].sum() == pytest.approx(10.0)
        assert mine["fouls_drawn"].sum() == pytest.approx(5.0)
        assert (mine["kind"] == "whole-season").all()

    def test_a_fully_covered_season_contributes_exactly_nothing(self):
        """The double-count gate, as an equality. Archive minutes match the
        API's, so there is no residual and there must be no rows."""
        arch = archive_rows("Covered Player", ["2023-09-02", "2023-10-07"], minutes=450.0)
        api = pd.DataFrame([api_row("Covered Player", "2023/24", 900.0, 4.0)])
        got = st.evidence(api, arch, offset=NEUTRAL)
        assert got[got["player"] == "Covered Player"].empty

    def test_a_partially_covered_season_contributes_the_residual(self):
        arch = archive_rows(
            "Half Seen", ["2023-09-02", "2023-10-07"], minutes=450.0, fouls=2.0
        )
        api = pd.DataFrame([api_row("Half Seen", "2023/24", 1800.0, 12.0)])
        got = st.evidence(api, arch, offset=NEUTRAL)
        mine = got[got["player"] == "Half Seen"]
        assert mine["minutes"].sum() == pytest.approx(900.0)
        assert mine["fouls_committed"].sum() == pytest.approx(8.0)
        assert (mine["kind"] == "residual").all()

    def test_residual_rows_are_dated_after_the_archive_stops(self):
        arch = archive_rows("Half Seen", ["2023-09-02", "2024-02-03"], minutes=450.0)
        api = pd.DataFrame([api_row("Half Seen", "2023/24", 1800.0, 12.0)])
        got = st.evidence(api, arch, offset=NEUTRAL)
        assert got["event_at"].min() > pd.Timestamp("2024-02-03", tz=UTC)
        assert got["event_at"].max() <= pd.Timestamp("2024-05-31", tz=UTC)

    def test_a_negative_residual_beyond_noise_is_excluded_and_counted(self):
        """API fouls below what the archive already saw means the identities
        or the season scope are wrong. That is an anomaly to surface, never
        evidence to clip into shape."""
        arch = archive_rows("Anomalous", ["2023-09-02"], minutes=900.0, fouls=10.0)
        api = pd.DataFrame([api_row("Anomalous", "2023/24", 1800.0, 3.0)])
        got = st.evidence(api, arch, offset=NEUTRAL)
        assert got[got["player"] == "Anomalous"].empty
        assert st.last_report()["anomalies"] == 1

    def test_minutes_present_and_fouls_absent_reads_as_zero_with_a_flag(self):
        """The fouls table omits zero-foul players. After the pagination
        repair, minutes-present-fouls-absent was verified to mean zero for 67
        of 69 determinable players, so it enters as exculpatory evidence,
        flagged, rather than being dropped as unknown."""
        api = pd.DataFrame([api_row("Clean Keeper", "2023/24", 2700.0, None)])
        got = st.evidence(api, archive_rows("Someone Else", ["2023-09-02"]), offset=NEUTRAL)
        mine = got[got["player"] == "Clean Keeper"]
        assert mine["minutes"].sum() == pytest.approx(2700.0)
        assert mine["fouls_committed"].sum() == 0.0
        assert (mine["kind"] == "zero-inferred").all()

    def test_no_minutes_means_no_rows_at_all(self):
        api = pd.DataFrame([api_row("Ghost", "2023/24", None, 5.0)])
        got = st.evidence(api, archive_rows("Someone Else", ["2023-09-02"]), offset=NEUTRAL)
        assert got[got["player"] == "Ghost"].empty

    def test_the_measured_offset_is_applied(self):
        api = pd.DataFrame([api_row("Novel Signing", "2023/24", 900.0, 10.5)])
        got = st.evidence(
            api,
            archive_rows("Someone Else", ["2023-09-02"]),
            offset={"seasons": {"2023/24": 1.05}, "global": {"ratio": 1.0}},
        )
        assert got["fouls_committed"].sum() == pytest.approx(10.0)


class TestKnowability:
    def test_a_completed_season_is_knowable_at_its_end(self):
        api = pd.DataFrame([api_row("Novel Signing", "2023/24", 900.0, 10.0)])
        got = st.evidence(api, archive_rows("Someone Else", ["2023-09-02"]), offset=NEUTRAL)
        assert (got["known_at"] == pd.Timestamp("2024-05-31", tz=UTC)).all()

    def test_an_in_progress_season_is_knowable_only_at_fetch(self):
        """Mid-season, the running total was published continuously, and we
        hold only the reading we took. Claiming it was knowable earlier is
        exactly the leakage the harness exists to prevent."""
        api = pd.DataFrame(
            [api_row("Current Player", "2026/27", 180.0, 3.0, fetched="2026-08-24T10:00:00+00:00")]
        )
        got = st.evidence(api, archive_rows("Someone Else", ["2023-09-02"]), offset=NEUTRAL)
        assert (got["known_at"] == pd.Timestamp("2026-08-24T10:00:00", tz=UTC)).all()
        assert got["event_at"].max() <= pd.Timestamp("2026-08-24T10:00:00", tz=UTC)


class TestTheBlend:
    def history(self):
        # A league of two positions with enough minutes to clear the position
        # prior threshold, plus the player under test.
        rows = [
            archive_rows(f"DM Filler {i}", [f"2023-{m:02d}-{d:02d}" for m in (9, 10, 11) for d in (2, 9, 16)], fouls=1.5)
            for i in range(30)
        ]
        return pd.concat(rows, ignore_index=True)

    def test_evidence_pulls_a_thin_player_from_the_prior(self):
        model = PlayerFoulModel(half_life_days=400, prior_matches=6)
        model.fit(self.history())
        as_of = pd.Timestamp("2026-08-24T12:00:00", tz=UTC)
        before, _ = model.player_rate("Novel Signing", as_of)

        api = pd.DataFrame([api_row("Novel Signing", "2025/26", 2700.0, 90.0)])
        model.attach_season_evidence(st.evidence(api, self.history(), offset=NEUTRAL))
        after, _ = model.player_rate("Novel Signing", as_of)
        assert after > before

    def test_an_archive_complete_player_is_untouched_to_the_last_digit(self):
        """The release gate from 34-final-plan.md: on player-seasons the
        archive already covers, blended and archive-only must be identical."""
        model = PlayerFoulModel()
        history = self.history()
        model.fit(history)
        as_of = pd.Timestamp("2026-08-24T12:00:00", tz=UTC)
        before, _ = model.player_rate("DM Filler 0", as_of)

        api = pd.DataFrame(
            [api_row("DM Filler 0", "2023/24", 9 * 90.0, 9 * 1.5)]
        )
        model.attach_season_evidence(st.evidence(api, history, offset=NEUTRAL))
        after, _ = model.player_rate("DM Filler 0", as_of)
        assert after == before

    def test_evidence_does_not_survive_a_refit(self):
        """A cache outliving fit is where the 2025 leakage lived. Same rule."""
        model = PlayerFoulModel()
        model.fit(self.history())
        api = pd.DataFrame([api_row("Novel Signing", "2025/26", 2700.0, 90.0)])
        model.attach_season_evidence(st.evidence(api, self.history(), offset=NEUTRAL))
        model.fit(self.history())
        as_of = pd.Timestamp("2026-08-24T12:00:00", tz=UTC)
        rate, _ = model.player_rate("Novel Signing", as_of)
        assert rate == model.prior_rate("Novel Signing")

    def test_evidence_not_yet_knowable_is_invisible(self):
        model = PlayerFoulModel()
        model.fit(self.history())
        api = pd.DataFrame([api_row("Novel Signing", "2025/26", 2700.0, 90.0)])
        model.attach_season_evidence(st.evidence(api, self.history(), offset=NEUTRAL))
        before_it_was_knowable = pd.Timestamp("2026-01-01", tz=UTC)
        rate, _ = model.player_rate("Novel Signing", before_it_was_knowable)
        assert rate == model.prior_rate("Novel Signing")

    def test_old_evidence_decays_like_any_other(self):
        """A 2006/07 total under a 70-day half-life is history, not evidence.
        Decay runs on the event date, so ancient seasons move nothing."""
        model = PlayerFoulModel(half_life_days=70, prior_matches=3)
        model.fit(self.history())
        as_of = pd.Timestamp("2026-08-24T12:00:00", tz=UTC)
        api = pd.DataFrame([api_row("Veteran Ghost", "2006/07", 2700.0, 90.0)])
        model.attach_season_evidence(st.evidence(api, self.history(), offset=NEUTRAL))
        rate, _ = model.player_rate("Veteran Ghost", as_of)
        assert rate == pytest.approx(model.prior_rate("Veteran Ghost"), rel=1e-6)
