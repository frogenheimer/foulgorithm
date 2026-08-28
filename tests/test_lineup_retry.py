"""The watcher retries, because its whole purpose is being present at T-60.

A missed lineup is a round predicted on the wrong eleven, and until now one
transient API failure mid-poll ended the entire afternoon's watch, while a
crash inside the publish itself killed the watcher uncaught. These tests fake
the clock and the poll and pin the discipline: a failed poll backs off and
continues, a crash is a failed poll rather than a dead process, and the run
reads as a failure only when a fixture actually kicked off unpublished while
the source was down.
"""

from datetime import UTC, datetime, timedelta

from foulgorithm.jobs import lineup_watch_live as live


class FakeFixture:
    def __init__(self, minutes_to_kickoff: float):
        self.home, self.away = "Fulham", "Chelsea"
        self.kickoff_utc = datetime.now(UTC) + timedelta(minutes=minutes_to_kickoff)


def wire(monkeypatch, fixtures, poll_codes):
    """No real sleeping, no network. Each element of poll_codes is one poll's
    outcome: an int exit code, or an exception instance to raise."""
    calls = {"polls": 0, "sleeps": []}
    codes = list(poll_codes)

    monkeypatch.setattr(live, "upcoming", lambda within=None: fixtures)
    monkeypatch.setattr(live.time, "sleep", lambda s: calls["sleeps"].append(s))
    monkeypatch.setattr(live, "_has_lineup", lambda f: True)

    from foulgorithm.jobs import changes, lineup_watch

    monkeypatch.setattr(changes, "run", lambda quiet=True: [])

    def fake_poll(*args, **kwargs):
        calls["polls"] += 1
        outcome = codes.pop(0) if codes else 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(lineup_watch, "run", fake_poll)
    return calls


class TestRetrying:
    def test_a_transient_failure_backs_off_and_still_publishes(self, monkeypatch):
        calls = wire(monkeypatch, [FakeFixture(30)], [2, 2, 0])
        assert live.run() == 0
        assert calls["polls"] == 3
        # Exponential: first retry at the poll interval, second at double it.
        assert calls["sleeps"][:2] == [live.POLL_SECONDS, live.POLL_SECONDS * 2]

    def test_a_crash_inside_the_publish_is_a_failed_poll_not_a_dead_watch(self, monkeypatch):
        calls = wire(monkeypatch, [FakeFixture(30)], [RuntimeError("boom"), 0])
        assert live.run() == 0
        assert calls["polls"] == 2

    def test_backoff_never_exceeds_its_ceiling(self, monkeypatch):
        calls = wire(monkeypatch, [FakeFixture(30)], [2] * 9 + [0])
        assert live.run() == 0
        assert max(calls["sleeps"]) <= live.MAX_BACKOFF_SECONDS

    def test_a_fixture_lost_while_the_source_was_down_reads_as_failure(self, monkeypatch):
        """A fake clock, not real milliseconds: the poll fails once before
        kickoff, then the next loop iteration finds the match under way."""
        start = datetime.now(UTC)
        fixture = FakeFixture(1)
        fixture.kickoff_utc = start + timedelta(minutes=1)
        wire(monkeypatch, [fixture], [2, 2, 2, 2])

        ticks = iter([start, start, start, start + timedelta(minutes=2)])
        last = start + timedelta(minutes=2)
        monkeypatch.setattr(live, "_now", lambda: next(ticks, None) or last)
        assert live.run() == 2

    def test_the_fixture_list_itself_is_retried_at_startup(self, monkeypatch):
        attempts = {"n": 0}

        def flaky(within=None):
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise RuntimeError("blip")
            return []

        monkeypatch.setattr(live, "upcoming", flaky)
        monkeypatch.setattr(live.time, "sleep", lambda s: None)
        from foulgorithm.jobs import changes

        monkeypatch.setattr(changes, "run", lambda quiet=True: [])
        assert live.run() == 1
        assert attempts["n"] == 2

    def test_a_source_dead_through_every_startup_attempt_is_loud(self, monkeypatch):
        def dead(within=None):
            raise RuntimeError("down")

        monkeypatch.setattr(live, "upcoming", dead)
        monkeypatch.setattr(live.time, "sleep", lambda s: None)
        from foulgorithm.jobs import changes

        monkeypatch.setattr(changes, "run", lambda quiet=True: [])
        assert live.run() == 2
