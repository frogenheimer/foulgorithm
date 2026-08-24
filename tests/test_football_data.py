"""Tests for the football-data.co.uk adapter.

Written before the implementation. Several of these encode traps verified on
21 August 2026 and documented in docs/02-data-sources.md:

  - a missing season file returns HTTP 300 with an HTML body, not a 404
  - new HxG/AxG columns appeared in 2026/27 between Referee and HS, so parsing
    by column position silently reads the wrong values
  - English cards exclude the first yellow of a second-yellow red
"""

from datetime import datetime, timezone

import pytest

from foulgorithm.sources.base import RawResponse, SourceError
from foulgorithm.sources.football_data import (
    REQUIRED_COLUMNS,
    parse,
    season_code,
    url_for,
    validate,
)

HEADER = (
    "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,Referee,HS,AS,HST,AST,"
    "HF,AF,HC,AC,HY,AY,HR,AR"
)
ROW = (
    "E0,17/08/2024,15:00,Arsenal,Wolves,2,0,H,Michael Oliver,17,5,8,1,"
    "17,14,9,2,2,1,0,0"
)

# The 2026/27 shape: HxG and AxG inserted between Referee and HS. Any parser
# reading by column index gets xG values where it expects shots.
HEADER_2627 = (
    "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,Referee,HxG,AxG,HS,AS,HST,AST,"
    "HF,AF,HC,AC,HY,AY,HR,AR"
)
ROW_2627 = (
    "E0,15/08/2026,20:00,Liverpool,Bournemouth,3,1,H,Anthony Taylor,2.41,0.87,"
    "16,7,9,3,11,13,8,3,3,2,0,0"
)


def raw(body: str, content_type: str = "text/csv", status: int = 200) -> RawResponse:
    return RawResponse(
        source="football_data",
        url="https://www.football-data.co.uk/mmz4281/2425/E0.csv",
        content=body.encode(),
        content_type=content_type,
        status_code=status,
        fetched_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )


class TestSeasonCode:
    @pytest.mark.parametrize(
        ("label", "expected"),
        [("2025-26", "2526"), ("2000-01", "0001"), ("1999-00", "9900"), ("2026-27", "2627")],
    )
    def test_converts_label_to_site_code(self, label, expected):
        assert season_code(label) == expected

    @pytest.mark.parametrize("bad", ["2025", "25-26", "2025/26", ""])
    def test_rejects_malformed_label(self, bad):
        with pytest.raises(ValueError):
            season_code(bad)


class TestUrl:
    def test_builds_premier_league_url(self):
        assert url_for("2025-26") == "https://www.football-data.co.uk/mmz4281/2526/E0.csv"

    def test_division_is_configurable(self):
        # Nothing about the adapter should hard-code the Premier League.
        assert url_for("2025-26", division="E1").endswith("/2526/E1.csv")


class TestValidate:
    def test_accepts_a_good_response(self):
        validate(raw(f"{HEADER}\n{ROW}"))

    def test_rejects_http_300(self):
        # A season file that does not exist yet returns 300 with an HTML body.
        # Checking only `response.ok` would ingest HTML as CSV.
        with pytest.raises(SourceError, match="300"):
            validate(raw("<html>Multiple Choices</html>", content_type="text/html", status=300))

    def test_rejects_html_content_type_even_on_200(self):
        with pytest.raises(SourceError, match="content type"):
            validate(raw("<html></html>", content_type="text/html"))

    def test_rejects_empty_body(self):
        with pytest.raises(SourceError, match="empty"):
            validate(raw(""))


class TestParse:
    def test_extracts_a_match(self):
        rows = parse(raw(f"{HEADER}\n{ROW}"))
        assert len(rows) == 1
        m = rows[0]
        assert m["home_team_raw"] == "Arsenal"
        assert m["away_team_raw"] == "Wolves"
        assert m["home_fouls"] == 17
        assert m["away_fouls"] == 14
        assert m["home_yellows"] == 2
        assert m["referee_raw"] == "Michael Oliver"

    def test_parses_by_name_not_position(self):
        # The regression test for the 2026/27 column shift. Reading by index
        # would put HxG (2.41) where HS (16) belongs.
        rows = parse(raw(f"{HEADER_2627}\n{ROW_2627}"))
        m = rows[0]
        assert m["home_fouls"] == 11
        assert m["away_fouls"] == 13
        assert m["home_shots"] == 16
        assert m["referee_raw"] == "Anthony Taylor"

    def test_missing_required_column_raises(self):
        # Never degrade a missing column into a default. The 2025 version turned
        # every failure into a neutral value and nobody noticed for months.
        header = HEADER.replace(",HF", ",XX")
        with pytest.raises(SourceError, match="HF"):
            parse(raw(f"{header}\n{ROW}"))

    def test_skips_trailing_blank_rows(self):
        rows = parse(raw(f"{HEADER}\n{ROW}\n,,,,,,,,,,,,,,,,,,,,\n"))
        assert len(rows) == 1

    def test_handles_two_digit_years(self):
        old = ROW.replace("17/08/2024", "17/08/04")
        rows = parse(raw(f"{HEADER}\n{old}"))
        assert rows[0]["kickoff_utc"].year == 2004

    def test_required_columns_include_the_disciplinary_fields(self):
        for col in ("HF", "AF", "HY", "AY", "HR", "AR", "Referee"):
            assert col in REQUIRED_COLUMNS


class TestKnownAt:
    def test_known_at_is_after_kickoff(self):
        m = parse(raw(f"{HEADER}\n{ROW}"))[0]
        assert m["known_at"] > m["kickoff_utc"]

    def test_known_at_is_conservative_when_time_is_missing(self):
        # No kickoff time means we assume a late kickoff, so known_at errs later
        # rather than earlier. Erring earlier would leak.
        no_time = ROW.replace(",15:00,", ",,")
        m = parse(raw(f"{HEADER}\n{no_time}"))[0]
        assert m["known_at"].hour >= 22


class TestRefreshingTheSeasonInProgress:
    """`fetch` serves any cached file forever, which is right for settled
    seasons and wrong for the running one: the moment the current season's
    file first lands on disk, the match store freezes, and with it the live
    opponent factors. Found designing the gameweek updater, before it bit.

    These use the real clock throughout: a fixed today against real file
    mtimes makes ages negative, which is its own little leakage lesson.
    """

    def label_now(self):
        from foulgorithm.sources import football_data as fd

        now = datetime.now(timezone.utc)
        start = now.year if now.month >= 8 else now.year - 1
        return now, f"{start}-{(start + 1) % 100:02d}", fd

    def test_the_running_season_is_refetched_when_stale(self, tmp_path, monkeypatch):
        import os
        import time

        now, label, fd = self.label_now()
        if now.month in (6, 7):
            pytest.skip("close season: nothing is in progress to refresh")

        cached = tmp_path / "football_data" / f"{fd.season_code(label)}_E0.csv"
        cached.parent.mkdir(parents=True)
        cached.write_text("old")
        stale = time.time() - 3 * 86400
        os.utime(cached, (stale, stale))

        fetched = []
        monkeypatch.setattr(
            fd, "fetch", lambda season, division="E0", cache_root=None: fetched.append(season)
        )
        got = fd.refresh_in_progress(cache_root=tmp_path)
        assert got == [label]
        assert fetched == [label]
        assert not cached.exists()

    def test_a_fresh_file_is_left_alone(self, tmp_path, monkeypatch):
        now, label, fd = self.label_now()
        if now.month in (6, 7):
            pytest.skip("close season: nothing is in progress to refresh")

        cached = tmp_path / "football_data" / f"{fd.season_code(label)}_E0.csv"
        cached.parent.mkdir(parents=True)
        cached.write_text("fresh just now")

        monkeypatch.setattr(
            fd, "fetch", lambda *a, **k: pytest.fail("a fresh file must not refetch")
        )
        assert fd.refresh_in_progress(cache_root=tmp_path) == []
        assert cached.exists()

    def test_settled_seasons_are_never_touched(self, tmp_path, monkeypatch):
        import os
        import time

        now, label, fd = self.label_now()
        if now.month in (6, 7):
            pytest.skip("close season: nothing is in progress to refresh")

        cached = tmp_path / "football_data" / "1819_E0.csv"
        cached.parent.mkdir(parents=True)
        cached.write_text("settled")
        stale = time.time() - 300 * 86400
        os.utime(cached, (stale, stale))

        # The current season has no file at all, so the refresh fetches it and
        # must fetch ONLY it: the settled file stays exactly as it was.
        fetched = []
        monkeypatch.setattr(
            fd, "fetch", lambda season, division="E0", cache_root=None: fetched.append(season)
        )
        got = fd.refresh_in_progress(cache_root=tmp_path)
        assert got == [label]
        assert fetched == [label]
        assert cached.read_text() == "settled"

    def test_close_season_has_nothing_in_progress(self, tmp_path):
        from foulgorithm.sources import football_data as fd

        got = fd.refresh_in_progress(
            cache_root=tmp_path, today=datetime(2025, 7, 1, tzinfo=timezone.utc)
        )
        assert got == []
