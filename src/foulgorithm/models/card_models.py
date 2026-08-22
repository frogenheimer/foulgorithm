"""Player cards: will this player be booked.

Binary, not a count, and the distinction is the whole point. Second yellows and
straight reds are rare enough that "how many cards" wastes the model's capacity
on a tail that almost never occurs. "Is he booked at all" is the question
bookmakers price and the one worth answering.

This is also the only market where real bookmaker odds exist to check ourselves
against: bet365 prices player yellow cards, and The Odds API carries
`player_to_receive_card` historically. Every other market we run is validated on
calibration alone.

**Read this before trusting the output.** Backtested over 11,789 walk-forward
predictions, this market is close to unpredictable with the data we hold:

| variant | log loss |
|---|---|
| own booking record only | 0.4314 |
| *league base rate* | *0.4336* |
| blended with expected fouls | 0.4347 |
| expected fouls only | 0.4556 |

The best version beats a model that knows nothing but the league average by
**0.5%**. Fouls per player, which beat their baseline by 4%, look strong by
comparison.

More surprising: **using expected fouls to predict cards makes it worse.** The
mechanism seemed obvious, since a booking usually IS one of the player's fouls,
but a foul-heavy player is not proportionally more bookable. Referees appear to
book for the KIND of foul rather than the count, and our data has no notion of
kind. `foul_weight` therefore defaults to zero, and the parameter is kept only
so the finding can be re-tested rather than taken on trust.

All variants also understate: they say about 12% where 15.6% happens, which is
consistent with the separate finding that cards have risen 16.3% since 2000
while fouls have fallen.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from foulgorithm.models.base import BinaryDistribution
from foulgorithm.models.player_models import _weights


class PlayerCardModel:
    """P(booked) from the player's own rate and his expected fouls."""

    market = "player_cards"

    def __init__(
        self,
        character_id: str = "house",
        half_life_days: float = 500.0,
        prior_matches: float = 10.0,
        foul_weight: float = 0.0,
    ):
        self.character_id = character_id
        self.half_life_days = half_life_days
        self.prior_matches = prior_matches
        # Defaults to zero because it was measured: adding expected fouls made
        # the model WORSE, not better. Kept as a parameter so the finding can be
        # re-tested if the data ever gains a notion of foul type.
        self.foul_weight = foul_weight
        self._history: pd.DataFrame | None = None
        self._league_rate = 0.12
        self._position_rate: dict[str, float] = {}
        self._player_position: dict[str, str] = {}
        self._fouls_per_card = 8.0

    def config(self) -> dict:
        return {
            "half_life_days": self.half_life_days,
            "prior_matches": self.prior_matches,
            "foul_weight": self.foul_weight,
        }

    def fit(self, history: pd.DataFrame) -> None:
        self._history = history
        played = history[history["minutes"] >= 20]
        booked = (played["yellows"].fillna(0) + played["reds"].fillna(0)) > 0
        self._league_rate = float(booked.mean())

        pos = played["position"].fillna("").astype(str).str.split(",").str[0].str.strip()
        frame = played.assign(_pos=pos, _booked=booked.astype(float))
        rates = frame.groupby("_pos")["_booked"].agg(["mean", "size"])
        self._position_rate = {
            str(k): float(r["mean"]) for k, r in rates.iterrows() if r["size"] >= 300
        }
        self._player_position = (
            frame.groupby("player")["_pos"].agg(lambda x: x.value_counts().index[0]).to_dict()
        )

        fouls = played["fouls_committed"].sum()
        cards = (played["yellows"].fillna(0) + played["reds"].fillna(0)).sum()
        if cards > 0:
            self._fouls_per_card = float(fouls / cards)

    def prior_rate(self, player: str) -> float:
        pos = self._player_position.get(player)
        if pos and pos in self._position_rate:
            return self._position_rate[pos]
        return self._league_rate

    def booking_rate(self, player: str, as_of) -> tuple[float, float]:
        """Shrunk, time-decayed share of appearances in which he was booked."""
        past = self._history[self._history["known_at"] <= as_of]
        rows = past[(past["player"] == player) & (past["minutes"] >= 20)]
        prior = self.prior_rate(player)
        if rows.empty:
            return prior, 0.0
        w = _weights(rows["known_at"], as_of, self.half_life_days)
        booked = ((rows["yellows"].fillna(0) + rows["reds"].fillna(0)) > 0).to_numpy(dtype=float)
        n = float(w.sum())
        rate = (float((w * booked).sum()) + self.prior_matches * prior) / (n + self.prior_matches)
        return float(rate), n

    def predict_one(
        self, player: str, as_of, expected_fouls: float, minutes: float = 90.0
    ) -> tuple[BinaryDistribution, dict]:
        own, effective = self.booking_rate(player, as_of)

        # A player expected to commit more fouls than average is likelier to be
        # booked, because the booking is usually one of those fouls. Converted
        # through the league's fouls-per-card ratio rather than a guess.
        from_fouls = 1.0 - np.exp(-expected_fouls / max(self._fouls_per_card, 1e-6))
        blended = (1 - self.foul_weight) * own + self.foul_weight * from_fouls

        # Scale by share of the match played: a substitute has less exposure.
        p = float(np.clip(blended * (minutes / 90.0), 0.005, 0.9))
        return BinaryDistribution(p), {
            "ownRate": round(own, 4),
            "fromFouls": round(float(from_fouls), 4),
            "expectedFouls": round(expected_fouls, 3),
            "effectiveMatches": round(effective, 1),
            "positionPrior": round(self.prior_rate(player), 4),
        }
