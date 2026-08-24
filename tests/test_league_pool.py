"""Pooling six leagues onto one scale, and refusing to do it silently.

Serie A runs 1.197 fouls per 90 against England's 0.972, a 23% gap, while
England's own eight-season spread is about 9%. Concatenating the files would
overstate every Italian player by a fifth. `29-why-leagues-differ.md` measured
the gap as roughly multiplicative and roughly uniform across positions, so a
single multiplicative intercept per league is the model, and these tests pin
the properties that make it safe: the reference league is unmoved, a planted
gap is recovered, offsets are fitted only on what was knowable, and a row
whose league is unknown is refused rather than assumed English.
"""

import numpy as np
import pandas as pd
import pytest

from foulgorithm.features import league_pool


def rows(league, player, n=20, fouls=1.0, minutes=90.0, start="2023-09-02"):
    dates = pd.to_datetime(start, utc=True) + pd.to_timedelta(np.arange(n) * 7, unit="D")
    return pd.DataFrame(
        {
            "player": player,
            "team": f"{league} FC",
            "opponent": f"{league} Rivals",
            "kickoff_utc": dates,
            "known_at": dates + pd.Timedelta(hours=3),
            "season": 2024,
            "position": "DM",
            "minutes": minutes,
            "fouls_committed": fouls,
            "fouls_drawn": fouls,
            "league": league,
        }
    )


def pooled(gap=1.23, players=26):
    """England at 1.0 fouls per 90 and Italy at `gap` times that.

    Sized past the real evidence floor on purpose, so these exercise the
    shipped default rather than a threshold loosened to suit them.
    """
    frames = []
    for i in range(players):
        frames.append(rows("ENG", f"Eng {i}", fouls=1.0))
        frames.append(rows("ITA", f"Ita {i}", fouls=gap))
    return pd.concat(frames, ignore_index=True)


class TestFittingTheOffsets:
    def test_the_reference_league_is_exactly_one(self):
        offsets = league_pool.league_offsets(pooled())
        assert offsets["ENG"] == 1.0

    def test_a_planted_gap_is_recovered(self):
        offsets = league_pool.league_offsets(pooled(gap=1.23))
        assert offsets["ITA"] == pytest.approx(1.23, abs=0.005)

    def test_each_market_gets_its_own_offset(self):
        """Committed and drawn are different processes and nothing guarantees
        one league's gap is the same in both."""
        frame = pooled()
        frame.loc[frame["league"] == "ITA", "fouls_drawn"] = 1.0
        committed = league_pool.league_offsets(frame, stat="fouls_committed")
        drawn = league_pool.league_offsets(frame, stat="fouls_drawn")
        assert committed["ITA"] > 1.2
        assert drawn["ITA"] == pytest.approx(1.0, abs=0.005)

    def test_a_league_with_too_little_evidence_is_left_out(self):
        frame = pd.concat([pooled(), rows("USA", "Usa One", n=1)], ignore_index=True)
        offsets = league_pool.league_offsets(frame, min_nineties=50)
        assert "USA" not in offsets

    def test_offsets_see_only_what_was_knowable(self):
        """Fitted inside a walk-forward fold, an offset that read the whole
        file would be the leak the harness exists to catch. A low floor here
        on purpose: this is about the time filter, and the volume floor has
        its own test above."""
        frame = pd.concat(
            [pooled(), rows("ESP", "Esp One", n=40, start="2024-06-01")],
            ignore_index=True,
        )
        cut = pd.Timestamp("2024-01-01", tz="UTC")
        early = league_pool.league_offsets(frame[frame["known_at"] <= cut], min_nineties=1)
        assert set(early) == {"ENG", "ITA"}
        assert "ESP" in league_pool.league_offsets(frame, min_nineties=1)


class TestRescaling:
    def test_the_reference_league_is_untouched_to_the_last_digit(self):
        frame = pooled()
        out = league_pool.to_reference(frame, {"ENG": 1.0, "ITA": 1.23})
        english = out[out["league"] == "ENG"]
        original = frame[frame["league"] == "ENG"]
        assert (english["fouls_committed"].to_numpy() == original["fouls_committed"].to_numpy()).all()

    def test_a_foreign_league_is_divided_down_to_the_reference(self):
        frame = pooled(gap=1.23)
        out = league_pool.to_reference(frame, league_pool.league_offsets(frame))
        rate = out.groupby("league").apply(
            lambda g: g["fouls_committed"].sum() / (g["minutes"].sum() / 90.0),
            include_groups=False,
        )
        assert rate["ITA"] == pytest.approx(rate["ENG"], abs=0.01)

    def test_minutes_are_never_touched(self):
        """The gap is in what gets whistled, not in how long anyone played."""
        frame = pooled()
        out = league_pool.to_reference(frame, {"ENG": 1.0, "ITA": 1.23})
        assert out["minutes"].sum() == frame["minutes"].sum()

    def test_a_league_with_no_fitted_offset_is_refused_not_assumed(self):
        """An unknown league silently treated as English is the missing-reads-
        as-average failure this project is built around."""
        frame = pd.concat([pooled(), rows("BRA", "Bra One")], ignore_index=True)
        with pytest.raises(ValueError, match="BRA"):
            league_pool.to_reference(frame, {"ENG": 1.0, "ITA": 1.23})

    def test_a_frame_with_no_league_column_is_refused(self):
        frame = pooled().drop(columns=["league"])
        with pytest.raises(ValueError, match="league"):
            league_pool.to_reference(frame, {"ENG": 1.0})


class TestRankTransfer:
    """The sharpest available check, from 29-why-leagues-differ.md: if the gap
    is interpretation rather than behaviour, a player who moves keeps his RANK
    among peers better than he keeps his RATE."""

    def moved(self, keeps_rank=True):
        frames, n = [], 24
        for i in range(12):
            before = 0.5 + i * 0.1
            after = before * 1.23 if keeps_rank else (1.7 - i * 0.1) * 1.23
            frames.append(rows("ENG", f"Mover {i}", n=n, fouls=before, start="2022-09-02"))
            frames.append(rows("ITA", f"Mover {i}", n=n, fouls=after, start="2023-09-02"))
        # Peers so each league has a distribution to rank within.
        for i in range(12):
            frames.append(rows("ENG", f"Eng Peer {i}", n=n, fouls=0.5 + i * 0.1))
            frames.append(rows("ITA", f"Ita Peer {i}", n=n, fouls=(0.5 + i * 0.1) * 1.23))
        return pd.concat(frames, ignore_index=True)

    def test_a_faithful_mover_shows_high_rank_correlation(self):
        got = league_pool.rank_transfer(self.moved(keeps_rank=True))
        assert got["rank_correlation"] > 0.9
        assert got["movers"] == 12

    def test_a_scrambled_mover_does_not(self):
        got = league_pool.rank_transfer(self.moved(keeps_rank=False))
        assert got["rank_correlation"] < -0.9

    def test_the_offset_removes_the_rate_discontinuity(self):
        """With the offset applied, a faithful mover's rate should not jump at
        the border. That is the guard against an intercept that is wrong."""
        got = league_pool.rank_transfer(self.moved(keeps_rank=True))
        assert abs(got["adjusted_rate_change"]) < abs(got["raw_rate_change"])
        assert abs(got["adjusted_rate_change"]) < 0.05
