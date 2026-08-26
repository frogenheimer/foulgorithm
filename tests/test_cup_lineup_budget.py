"""The lineup watch has to fit inside 100 requests a day.

The free API-Football plan meters 100 requests a day, 10 a minute, reset at
midnight UTC with no rollover (docs/02-data-sources). The old watcher polled
per fixture every 90 seconds, which was fine for the one hand-fed tie it was
written for: about 47 requests for a full watch.

The slate is not one tie any more. An FA Cup third round can leave ten
qualifying ties on one afternoon, and ten fixtures times 47 cycles is 470
requests. The watch would die four fifths of the way through the round and we
would get no elevens at all, which is worse than getting them for one tie.

Two changes, both tested here. One request covers every tie in the window
instead of one each, and the cadence drops to five minutes because cup elevens
land 40 to 70 minutes out and nobody is betting these pages.
"""

import pytest

from foulgorithm.jobs import cup_watch


class TestBatching:
    def test_a_whole_window_costs_one_request(self):
        assert cup_watch.requests_per_cycle(10) == 1

    def test_more_ties_than_one_batch_holds_costs_one_request_each_batch(self):
        # API-Football takes at most 20 ids in a single fixtures call.
        assert cup_watch.requests_per_cycle(21) == 2
        assert cup_watch.requests_per_cycle(40) == 2
        assert cup_watch.requests_per_cycle(41) == 3

    def test_an_empty_window_costs_nothing(self):
        assert cup_watch.requests_per_cycle(0) == 0


class TestBudget:
    def test_a_ten_tie_round_fits_inside_the_daily_cap(self):
        assert cup_watch.watch_cost(ties=10) <= cup_watch.DAILY_CAP

    def test_a_full_third_round_slate_still_fits(self):
        # 44 of the 92 league clubs are ours, so 22 ties is the ceiling.
        assert cup_watch.watch_cost(ties=22) <= cup_watch.DAILY_CAP

    def test_the_old_per_fixture_cadence_would_not_have(self):
        # The bug, stated as a test so nobody reinstates it by tidying.
        old = 10 * (cup_watch.LOOK_FROM.total_seconds() / 90)
        assert old > cup_watch.DAILY_CAP

    def test_the_cost_leaves_room_for_the_slate_pull_and_the_publish(self):
        # Two more requests a day pull the two cups' fixture lists.
        assert cup_watch.watch_cost(ties=22) + 2 <= cup_watch.DAILY_CAP


class TestCadence:
    def test_polling_is_five_minutes_not_ninety_seconds(self):
        assert cup_watch.POLL_SECONDS == 300

    def test_the_window_still_opens_well_before_kickoff(self):
        # API-Football posts cup elevens less punctually than the league's
        # T-60, so the watch opens earlier and that must not regress.
        assert cup_watch.LOOK_FROM.total_seconds() >= 70 * 60


class TestBatches:
    def test_ids_are_grouped_into_batches_of_twenty(self):
        assert cup_watch.batches(list(range(45))) == [
            list(range(20)), list(range(20, 40)), list(range(40, 45))
        ]

    def test_a_short_list_is_one_batch(self):
        assert cup_watch.batches([1, 2, 3]) == [[1, 2, 3]]

    def test_nothing_batches_to_nothing(self):
        assert cup_watch.batches([]) == []
