"""The league watcher must SEE team sheets before kickoff, always.

On 28 August 2026 Palace v City sat at status "upcoming" at T-20 with both
elevens posted, and for_round, which only read live or finished fixtures,
returned nothing. It would only have caught them after kickoff, when the
binding rule ignores them. These pin the gate so it cannot drift back."""

from datetime import UTC, datetime, timedelta

from foulgorithm.sources import lineups, pulselive

NOW = datetime(2026, 8, 28, 18, 30, tzinfo=UTC)


def fx(fid, home, away, hours, status="U"):
    return type(
        "F",
        (),
        {
            "id": fid,
            "home": home,
            "away": away,
            "kickoff_utc": NOW + timedelta(hours=hours),
            "status": status,
        },
    )()


def detail_with_sheets(_fid):
    return {
        "teams": [
            {"team": {"id": 6, "name": "Crystal Palace"}},
            {"team": {"id": 11, "name": "Manchester City"}},
        ],
        "teamLists": [
            {
                "teamId": 6,
                "formation": None,
                "lineup": [{"name": {"display": f"P{i}"}, "matchPosition": "D"} for i in range(11)],
                "substitutes": [],
            },
            {
                "teamId": 11,
                "formation": None,
                "lineup": [{"name": {"display": f"C{i}"}, "matchPosition": "M"} for i in range(11)],
                "substitutes": [],
            },
        ],
    }


class TestTheGate:
    def test_an_upcoming_fixture_inside_three_hours_is_read(self, monkeypatch):
        monkeypatch.setattr(
            pulselive,
            "fixtures",
            lambda season_id=None: [fx(1, "Crystal Palace", "Manchester City", 0.5)],
        )
        monkeypatch.setattr(pulselive, "fixture_detail", detail_with_sheets)
        out = lineups.for_round(now=NOW)
        assert any(k.endswith("|Crystal Palace v Man City") for k in out), list(out)

    def test_an_upcoming_fixture_tomorrow_is_not_fetched(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            pulselive,
            "fixtures",
            lambda season_id=None: [fx(2, "Crystal Palace", "Manchester City", 20)],
        )
        monkeypatch.setattr(
            pulselive,
            "fixture_detail",
            lambda fid: calls.append(fid) or {"teams": [], "teamLists": [None, None]},
        )
        assert lineups.for_round(now=NOW) == {}
        assert calls == []

    def test_live_and_finished_fixtures_are_still_read(self, monkeypatch):
        monkeypatch.setattr(
            pulselive,
            "fixtures",
            lambda season_id=None: [fx(3, "Crystal Palace", "Manchester City", -1, status="L")],
        )
        monkeypatch.setattr(pulselive, "fixture_detail", detail_with_sheets)
        assert lineups.for_round(now=NOW)
