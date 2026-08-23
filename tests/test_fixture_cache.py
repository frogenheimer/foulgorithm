"""The fixture list is cached for the process, and some processes outlive it.

Profiling one publish run found 1,004 HTTP requests taking 89 of 232 seconds,
almost all of them the same unchanging fixture list fetched again inside a
per-player loop. Caching it is the single biggest saving available.

The risk it introduces is the opposite failure: a long-running job served a list
it fetched hours ago. The lineup watcher runs for five and a half hours and
exists to notice kickoff moves and referee appointments, so it is exactly the
process that must not be.
"""

import pytest

from foulgorithm.sources import pulselive


class TestItIsCached:
    def test_the_list_is_fetched_once(self, monkeypatch):
        calls = []

        def fake_get(path):
            calls.append(path)
            return {"content": []}

        pulselive.forget()
        monkeypatch.setattr(pulselive, "_get", fake_get)
        monkeypatch.setattr(pulselive, "current_season_id", lambda: 1)

        pulselive.fixtures(season_id=1)
        pulselive.fixtures(season_id=1)
        pulselive.fixtures(season_id=1)
        assert len(calls) == 1, f"fetched {len(calls)} times, should be once"

    def test_a_different_season_is_a_different_fetch(self, monkeypatch):
        calls = []
        pulselive.forget()
        monkeypatch.setattr(pulselive, "_get", lambda p: (calls.append(p), {"content": []})[1])

        pulselive.fixtures(season_id=1)
        pulselive.fixtures(season_id=2)
        assert len(calls) == 2


class TestItCanBeForgotten:
    def test_forget_makes_the_next_call_fetch_again(self, monkeypatch):
        calls = []
        pulselive.forget()
        monkeypatch.setattr(pulselive, "_get", lambda p: (calls.append(p), {"content": []})[1])

        pulselive.fixtures(season_id=1)
        pulselive.forget()
        pulselive.fixtures(season_id=1)
        assert len(calls) == 2, "a forgotten cache must refetch"


class TestTheWatcherDoesNotGoStale:
    """The job that polls for five hours has to drop the cache each round.

    Without this the caching turns a working watcher into one that reports the
    kickoff times it saw when it started, which is a worse bug than the slowness
    it was added to fix.
    """

    def test_the_live_watcher_forgets_before_polling(self):
        from pathlib import Path

        source = Path("src/foulgorithm/jobs/lineup_watch_live.py").read_text()
        assert "forget()" in source, (
            "the live watcher must clear the fixture cache each round, or it "
            "polls for hours against a list it fetched once"
        )
