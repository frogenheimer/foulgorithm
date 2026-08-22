"""Player foul models, one per character.

Structure of every model here:

    expected fouls = player rate per 90
                   x expected minutes / 90
                   x opponent factor
                   x referee factor

The four parts are shared. What differs per character is how much each is
trusted: how far back they look, how hard they shrink a thin sample, how much
weight they give the opponent, and how confident the resulting distribution is.

Minutes matter more than anything else here. A 0.9-per-90 fouler who plays 25
minutes is a completely different proposition from one who plays 90, and the
2025 version had no concept of minutes at all.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from foulgorithm.models.base import CountDistribution, register
from foulgorithm.models.match_models import negbin_pmf

LEAGUE_PRIOR_MATCHES = 12.0


def _weights(known_at: pd.Series, as_of, half_life_days: float) -> np.ndarray:
    age = (pd.Timestamp(as_of) - known_at).dt.total_seconds().to_numpy() / 86400.0
    return np.power(0.5, np.maximum(age, 0.0) / half_life_days)


class PlayerFoulModel:
    """Shared machinery. Character differences live in the constructor."""

    market = "player_fouls_committed"
    stat = "fouls_committed"

    def __init__(
        self,
        character_id: str,
        half_life_days: float,
        prior_matches: float,
        opponent_weight: float,
        dispersion: float,
        amplify: float = 1.0,
        label: str | None = None,
    ):
        self.character_id = character_id
        self.half_life_days = half_life_days
        self.prior_matches = prior_matches
        self.opponent_weight = opponent_weight
        self.dispersion = dispersion
        self.amplify = amplify
        self.label = label or character_id
        self._history: pd.DataFrame | None = None
        self._league_rate = 1.0
        self._position_rate: dict[str, float] = {}
        self._player_position: dict[str, str] = {}
        self._default_minutes = 70.0

    def config(self) -> dict:
        return {
            "half_life_days": self.half_life_days,
            "prior_matches": self.prior_matches,
            "opponent_weight": self.opponent_weight,
            "dispersion": self.dispersion,
            "amplify": self.amplify,
        }

    def fit(self, history: pd.DataFrame) -> None:
        self._history = history
        minutes = history["minutes"].sum()
        self._league_rate = float(history[self.stat].sum() / (minutes / 90.0))

        # Shrink toward the player's POSITION, not the league.
        #
        # Shrinking a goalkeeper toward the league average implies he fouls like
        # a midfielder, and with a short memory and a weak prior one recent foul
        # then explodes his rate. That is how Alan ended up backing four
        # goalkeepers. Position priors make the same short memory behave.
        pos = history["position"].fillna("").astype(str).str.split(",").str[0].str.strip()
        grouped = history.assign(_pos=pos).groupby("_pos")
        rates = grouped.apply(
            lambda g: g[self.stat].sum() / max(g["minutes"].sum() / 90.0, 1e-6),
            include_groups=False,
        )
        counts = grouped["minutes"].sum() / 90.0
        self._position_rate = {
            str(k): float(v) for k, v in rates.items() if counts.get(k, 0) >= 200
        }
        # What a player who features actually plays, so an unseen player has a
        # defensible prior rather than a zero.
        featured = history[history["minutes"] >= 20]["minutes"]
        if len(featured):
            self._default_minutes = float(featured.median())


        self._player_position = (
            history.assign(_pos=pos).groupby("player")["_pos"].agg(
                lambda x: x.value_counts().index[0]
            ).to_dict()
        )

    def dispersion_at(self, mean: float) -> float:
        """Residual dispersion. Deliberately a constant.

        A count-dependent version was fitted and measured: the slope came out at
        0.014 and changed the 3+ bias from -0.0149 to -0.0145, which is noise.
        The hypothesis that a fat tail on low-mean players caused the
        overconfidence was simply wrong, and the code is gone rather than left
        in place looking like it does something.

        What was actually wrong is the VALUE. See the class docstring.
        """
        return max(self.dispersion, 1.0001)

    def prior_rate(self, player: str) -> float:
        """The rate we assume before seeing this player's own record."""
        pos = self._player_position.get(player)
        if pos and pos in self._position_rate:
            return self._position_rate[pos]
        return self._league_rate

    def _visible(self, as_of) -> pd.DataFrame:
        return self._history[self._history["known_at"] <= as_of]

    def player_rate(self, player: str, as_of) -> tuple[float, float]:
        """Shrunk, time-decayed rate per 90. Returns (rate, effective matches)."""
        past = self._visible(as_of)
        rows = past[past["player"] == player]
        prior = self.prior_rate(player)
        if rows.empty:
            return prior, 0.0

        w = _weights(rows["known_at"], as_of, self.half_life_days)
        nineties = (rows["minutes"].to_numpy() / 90.0) * w
        events = rows[self.stat].to_numpy() * w
        prior90 = self.prior_matches
        rate = (events.sum() + prior90 * prior) / (nineties.sum() + prior90)
        return float(rate), float(w.sum())

    def expected_minutes(self, player: str, as_of, starter: bool = True) -> float:
        """Recent minutes, time-decayed, with a fallback for unseen players.

        Returning 0.0 for a player with no history was a hole, not a
        conservative estimate: his expected fouls then collapsed to nothing.
        Promoted clubs are mostly such players, which is how Hull came to show
        2.31 expected fouls against Manchester United's 10.2.

        A player we have never seen but who is expected to feature gets the
        league's typical starter minutes, which is the honest prior. The
        uncertainty is expressed by marking his evidence thin, not by pretending
        he will not play.
        """
        past = self._visible(as_of)
        rows = past[past["player"] == player].tail(10)
        if rows.empty:
            return self._default_minutes if starter else self._default_minutes * 0.35
        w = _weights(rows["known_at"], as_of, self.half_life_days)
        return float(np.average(rows["minutes"].to_numpy(), weights=w))

    def opponent_factor(self, opponent: str, as_of) -> float:
        """How many fouls this opponent draws out of teams, relative to league."""
        past = self._visible(as_of)
        rows = past[past["opponent"] == opponent]
        if len(rows) < 200:
            return 1.0
        w = _weights(rows["known_at"], as_of, self.half_life_days)
        nineties = (rows["minutes"].to_numpy() / 90.0) * w
        rate = float((rows[self.stat].to_numpy() * w).sum() / max(nineties.sum(), 1e-6))
        raw = rate / max(self._league_rate, 1e-6)
        # Pull toward 1 by the character's willingness to trust the matchup.
        return 1.0 + (raw - 1.0) * self.opponent_weight

    def predict_one(
        self, player: str, opponent: str, as_of, referee_factor: float = 1.0
    ) -> tuple[CountDistribution, dict]:
        rate, effective = self.player_rate(player, as_of)
        minutes = self.expected_minutes(player, as_of)
        opp = self.opponent_factor(opponent, as_of)

        mean = rate * (minutes / 90.0) * opp * referee_factor
        if self.amplify != 1.0:
            base = self.prior_rate(player) * (minutes / 90.0)
            mean = base + (mean - base) * self.amplify
        mean = max(mean, 0.02)

        dist = negbin_pmf(mean, mean * self.dispersion_at(mean))
        return dist, {
            "ratePer90": round(rate, 3),
            "expectedMinutes": round(minutes, 1),
            "opponentFactor": round(opp, 3),
            "refereeFactor": round(referee_factor, 3),
            "effectiveMatches": round(effective, 1),
        }


class PlayerFouledModel(PlayerFoulModel):
    """Same machinery, opposite market: fouls the player draws."""

    market = "player_fouls_drawn"
    stat = "fouls_drawn"


# Each character's temperament, expressed as four numbers.
#
#   half_life        how far back they look
#   prior_matches    how hard they shrink a thin sample toward the league
#   opponent_weight  how much they trust the matchup
#   dispersion       how confident the published distribution is
#   amplify          how far they push a deviation from average
CHARACTER_SETTINGS: dict[str, dict] = {
    # Anger: only the recent past exists, barely shrinks, exaggerates, overconfident.
    "alan": dict(half_life_days=70, prior_matches=3, opponent_weight=1.3, dispersion=1.00, amplify=1.3),
    # Lust: long memory for reputation, trusts the name over the matchup.
    "lily": dict(half_life_days=1200, prior_matches=8, opponent_weight=0.5, dispersion=1.10, amplify=1.1),
    # Violence: reads the matchup hardest, medium memory.
    "valentina": dict(half_life_days=400, prior_matches=6, opponent_weight=1.6, dispersion=1.05, amplify=1.15),
    # Terror: long memory, heavy shrinkage, wide distribution, never exaggerates.
    "tayler": dict(half_life_days=1000, prior_matches=30, opponent_weight=0.4, dispersion=1.25, amplify=1.0),
    # Bravery: short-to-medium memory, trusts thin evidence others shrink away.
    "bdog": dict(half_life_days=300, prior_matches=2, opponent_weight=1.1, dispersion=1.02, amplify=1.2),
}


def build(character_id: str, market: str = "player_fouls_committed") -> PlayerFoulModel:
    settings = CHARACTER_SETTINGS[character_id]
    cls = PlayerFoulModel if market == "player_fouls_committed" else PlayerFouledModel
    return cls(character_id=character_id, **settings)


def build_all(market: str = "player_fouls_committed") -> list[PlayerFoulModel]:
    return [build(cid, market) for cid in CHARACTER_SETTINGS]
