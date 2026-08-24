"""Settle wakes derived from real kickoffs, one per matchday.

Step 2 of docs/33-settle-schedule.md. The Monday and Thursday crons left
windows wide enough that a player featuring twice was unattributable and
skipped forever. The fix mirrors the lineup rescheduler: read the fixture
list, wake once per matchday after the last match's stats have posted.

The lag matters more than the bundling. The settle run refuses to snapshot
while any fixture is inside STATS_DELAY of kickoff, so a wake that fires too
early defers and the matchday waits for the backstop cron. The lag therefore
clears STATS_DELAY with room for GitHub's scheduler running late, which it
does under load.
"""

from datetime import datetime, timedelta, timezone

from foulgorithm.jobs import schedule


def fixture(when: str):
    class F:
        kickoff_utc = datetime.fromisoformat(when).replace(tzinfo=timezone.utc)

    return F()


def future_day(days_ahead: int, hour: int, minute: int = 0) -> str:
    when = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    return when.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()[:16]


class TestSettleWindows:
    def test_a_matchday_gets_one_wake_after_its_last_kickoff(self):
        fixtures = [
            fixture(future_day(2, 12, 30)),
            fixture(future_day(2, 15, 0)),
            fixture(future_day(2, 17, 30)),
        ]
        got = schedule.settle_windows(fixtures)
        assert len(got) == 1
        assert got[0] == fixtures[2].kickoff_utc + schedule.SETTLE_LAG

    def test_two_matchdays_get_two_wakes(self):
        fixtures = [fixture(future_day(2, 15)), fixture(future_day(3, 14))]
        assert len(schedule.settle_windows(fixtures)) == 2

    def test_the_lag_clears_the_stats_delay(self):
        """A wake inside STATS_DELAY would meet its own deferral guard and
        the whole matchday would wait for the backstop cron."""
        from foulgorithm.store.players import STATS_DELAY

        assert schedule.SETTLE_LAG > STATS_DELAY

    def test_past_and_far_future_fixtures_are_ignored(self):
        fixtures = [fixture("2020-01-01T15:00"), fixture(future_day(40, 15))]
        assert schedule.settle_windows(fixtures) == []


class TestRewritingTheWorkflow:
    def workflow(self, tmp_path):
        path = tmp_path / "settle.yml"
        path.write_text(
            "on:\n  schedule:\n"
            '    - cron: "0 9 * * 1"\n'
            f"{schedule.SETTLE_START}\n{schedule.SETTLE_END}\n"
            "  workflow_dispatch:\n"
        )
        return path

    def test_wakes_land_between_the_markers(self, tmp_path, monkeypatch):
        path = self.workflow(tmp_path)
        when = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(days=2)
        monkeypatch.setattr(
            schedule, "settle_windows", lambda fixtures, horizon_days=14: [when]
        )
        assert schedule.rewrite_settle([], path) == 0
        text = path.read_text()
        assert f'- cron: "{when.minute} {when.hour} {when.day} {when.month} *"' in text
        # The backstop cron survives: generated wakes add to it, never replace it.
        assert '- cron: "0 9 * * 1"' in text

    def test_an_unchanged_schedule_says_so(self, tmp_path, monkeypatch):
        path = self.workflow(tmp_path)
        when = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(days=2)
        monkeypatch.setattr(
            schedule, "settle_windows", lambda fixtures, horizon_days=14: [when]
        )
        assert schedule.rewrite_settle([], path) == 0
        assert schedule.rewrite_settle([], path) == 1

    def test_a_workflow_without_markers_is_refused(self, tmp_path):
        path = tmp_path / "settle.yml"
        path.write_text("on:\n  schedule:\n")
        assert schedule.rewrite_settle([], path) == 2
