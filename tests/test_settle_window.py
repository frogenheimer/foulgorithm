"""Only the games this snapshot window covers may be graded from it.

On 28 August 2026 the first evening settle graded 141 of the PREVIOUS
round's still-open claims with that night's diffs: the settled-fixtures gate
was "every completed game this season", so a player unused last week whose
first outcome arrived tonight settled last week's claim about him. The gate
is now the window: complete, and kicked off after the previous snapshot."""

from datetime import UTC, datetime, timedelta

from foulgorithm.jobs import settle

NOW = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)
PREVIOUS = "2026-08-24T22:22:23+00:00"


def fx(home, away, hours_before_now, complete=True):
    return type("F", (), {
        "home": home, "away": away, "complete": complete,
        "kickoff_utc": NOW - timedelta(hours=hours_before_now),
    })()


FIXTURES = [
    fx("Crystal Palace", "Manchester City", 2),            # tonight
    fx("Everton", "Crystal Palace", 6 * 24),               # last week, already settled
    fx("Liverpool", "Nottingham Forest", -15, complete=False),  # tomorrow
]


def test_only_games_after_the_previous_snapshot_are_settled():
    assert settle.settled_fixtures(FIXTURES, since=PREVIOUS) == {"Crystal Palace v Man City"}


def test_an_unfinished_game_is_never_settled():
    assert "Liverpool v Nott'm Forest" not in settle.settled_fixtures(FIXTURES, since=PREVIOUS)


def test_without_a_previous_snapshot_every_completed_game_counts():
    assert settle.settled_fixtures(FIXTURES, since=None) == {
        "Crystal Palace v Man City", "Everton v Crystal Palace"
    }
