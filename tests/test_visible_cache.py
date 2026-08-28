"""Caching the point-in-time filter must not leak the future into it.

`_visible(as_of)` re-filtered the whole history on every call and a publish run
makes about twenty-five thousand of them, all with the same `as_of`. Caching it
is a large saving and also the exact place a leakage bug would live, so the
cache is keyed on `as_of` and dropped whenever the model is refitted.

The canary in `tests/test_leakage.py` covers the model. These cover the cache.
"""

import pandas as pd

from foulgorithm.models import player_models as pm


def history():
    rows = []
    for day in range(1, 29):
        stamp = pd.Timestamp(f"2026-01-{day:02d}", tz="UTC")
        for name in ("A", "B"):
            rows.append(
                {
                    "player": name,
                    "team": "T",
                    "opponent": "O",
                    "venue": "H",
                    "kickoff_utc": stamp,
                    "known_at": stamp,
                    "season": "2025-26",
                    "position": "MF",
                    "minutes": 90,
                    "fouls_committed": 2,
                    "fouls_drawn": 1,
                    "yellows": 0,
                    "reds": 0,
                    "tackles_won": 1,
                    "interceptions": 1,
                    "source": "test",
                }
            )
    return pd.DataFrame(rows)


class TestTheCacheRespectsTime:
    def test_a_later_as_of_sees_more(self):
        model = pm.build("tayler")
        model.fit(history())
        early = model._visible(pd.Timestamp("2026-01-10", tz="UTC"))
        late = model._visible(pd.Timestamp("2026-01-27", tz="UTC"))
        assert len(late) > len(early)

    def test_asking_twice_gives_the_same_rows(self):
        model = pm.build("tayler")
        model.fit(history())
        at = pd.Timestamp("2026-01-10", tz="UTC")
        assert len(model._visible(at)) == len(model._visible(at))

    def test_nothing_after_as_of_is_ever_returned(self):
        model = pm.build("tayler")
        model.fit(history())
        at = pd.Timestamp("2026-01-15", tz="UTC")
        model._visible(pd.Timestamp("2026-01-28", tz="UTC"))  # warm it with a later view
        assert model._visible(at)["known_at"].max() <= at

    def test_refitting_drops_the_cache(self):
        """Otherwise a walk-forward fold answers with the previous fold's data."""
        model = pm.build("tayler")
        full = history()
        model.fit(full)
        at = pd.Timestamp("2026-01-27", tz="UTC")
        before = len(model._visible(at))

        model.fit(full[full["known_at"] <= pd.Timestamp("2026-01-05", tz="UTC")])
        after = len(model._visible(at))
        assert after < before, "refitting on less data must not return the old view"
