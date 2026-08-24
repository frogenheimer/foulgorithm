"""The reconstruction the C1 gate stands on.

The study replays the frozen year with season totals rebuilt from withheld
archive rows. What must hold: the reconstruction sums exactly what a settle
job would have held, and never a row the timestamp had not yet seen, because
a leaky reconstruction would flatter the variant it feeds and the gate would
pass on manufactured evidence.
"""

import pandas as pd

from foulgorithm.backtest import season_total_study as study


def rows(player, dates, minutes=90.0, fouls=2.0):
    stamps = pd.to_datetime(dates, utc=True)
    return pd.DataFrame(
        {
            "player": player,
            "kickoff_utc": stamps,
            "known_at": stamps + pd.Timedelta(hours=3),
            "season": 2025,
            "minutes": minutes,
            "fouls_committed": fouls,
            "fouls_drawn": 1.0,
        }
    )


class TestTheReconstruction:
    def test_totals_are_summed_up_to_the_timestamp_and_no_further(self):
        withheld = pd.concat(
            [rows("A Player", ["2024-10-05", "2024-10-19", "2024-11-02"])],
            ignore_index=True,
        )
        got = study.running_total_frame(withheld, pd.Timestamp("2024-10-25", tz="UTC"))
        assert len(got) == 1
        assert got.iloc[0]["mins_played"] == 180.0
        assert got.iloc[0]["fouls"] == 4.0

    def test_a_reading_carries_the_timestamp_it_was_taken_at(self):
        withheld = rows("A Player", ["2024-10-05"])
        as_of = pd.Timestamp("2024-10-25", tz="UTC")
        got = study.running_total_frame(withheld, as_of)
        assert got.iloc[0]["fetchedAt"] == as_of.isoformat()
        assert got.iloc[0]["season"] == "2024/25"

    def test_nothing_visible_means_an_empty_frame_not_a_crash(self):
        withheld = rows("A Player", ["2024-10-05"])
        got = study.running_total_frame(withheld, pd.Timestamp("2024-09-20", tz="UTC"))
        assert got.empty
