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

from dataclasses import dataclass

from foulgorithm.models.base import CountDistribution, register
from foulgorithm.models.match_models import negbin_pmf

LEAGUE_PRIOR_MATCHES = 12.0

# Below this, a player is treated as having come off the bench rather than
# started. Substitute appearances cluster well under it and starts well over.
STARTER_MINUTES = 60.0


@dataclass(frozen=True)
class MinutesProfile:
    """How a player's minutes are actually distributed, not their average.

    Averaging is the problem this exists to fix. A rotation player alternating
    90 minutes and 0 averages 45, and he has never once played 45 minutes.
    Pricing him as a steady half-match player understates both his quiet games
    and his busy ones.
    """

    p_start: float
    p_sub: float
    p_unused: float
    minutes_if_start: float
    minutes_if_sub: float
    appearances: float

    def mean_minutes(self) -> float:
        return self.p_start * self.minutes_if_start + self.p_sub * self.minutes_if_sub

    def branches(self) -> list[tuple[float, float]]:
        """(probability, minutes) per branch, unused first. Weights sum to one."""
        return [
            (self.p_unused, 0.0),
            (self.p_start, self.minutes_if_start),
            (self.p_sub, self.minutes_if_sub),
        ]


def _weights(known_at: pd.Series, as_of, half_life_days: float) -> np.ndarray:
    age = (pd.Timestamp(as_of) - known_at).dt.total_seconds().to_numpy() / 86400.0
    return np.power(0.5, np.maximum(age, 0.0) / half_life_days)


class PlayerFoulModel:
    """Shared machinery. Character differences live in the constructor."""

    market = "player_fouls_committed"
    stat = "fouls_committed"

    def __init__(
        self,
        character_id: str = "house",
        half_life_days: float = 400.0,
        prior_matches: float = 6.0,
        opponent_weight: float = 1.0,
        dispersion: float = 1.05,
        amplify: float = 1.0,
        label: str | None = None,
        reads_head_to_head: bool = False,
    ):
        self.character_id = character_id
        self.half_life_days = half_life_days
        self.prior_matches = prior_matches
        self.opponent_weight = opponent_weight
        self.dispersion = dispersion
        self.amplify = amplify
        # Valentina's alone. The other four differ from each other by how much
        # they trust the same numbers; this is a question none of them asks.
        self.reads_head_to_head = reads_head_to_head
        self._pairings: dict = {}
        self.label = label or character_id
        self._history: pd.DataFrame | None = None
        self._league_rate = 1.0
        self._visible_cache: dict = {}
        self._position_rate: dict[str, float] = {}
        self._player_position: dict[str, str] = {}
        self._default_minutes = 70.0

    def fit_pairings(self, matches, as_of=None) -> None:
        """Learn which fixtures run hot. Only Valentina asks, so only she stores it."""
        if not self.reads_head_to_head:
            return
        from foulgorithm.features import head_to_head

        self._pairings = head_to_head.residuals_from(matches, as_of)

    def head_to_head_factor(self, team: str, opponent: str) -> float:
        if not self.reads_head_to_head or not self._pairings:
            return 1.0
        from foulgorithm.features import head_to_head

        return head_to_head.adjustment(team, opponent, self._pairings)

    def config(self) -> dict:
        return {
            "half_life_days": self.half_life_days,
            "prior_matches": self.prior_matches,
            "opponent_weight": self.opponent_weight,
            "dispersion": self.dispersion,
            "amplify": self.amplify,
            "readsHeadToHead": self.reads_head_to_head,
        }

    def fit(self, history: pd.DataFrame) -> None:
        self._history = history
        # Never survives a refit. See _visible.
        self._visible_cache: dict = {}
        minutes = float(history["minutes"].sum())
        # A history with no minutes in it divides by zero and makes the league
        # rate NaN, which then silently poisons every prior and every shrunk
        # rate downstream without raising anywhere. Refusing is louder and the
        # only honest option: there is no league rate to be had.
        if minutes <= 0:
            raise ValueError(
                "cannot fit on a history with no minutes played: there is no "
                "league rate to shrink toward"
            )
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
        """History known by `as_of`, cached for the fit it belongs to.

        Filtering the whole frame ran on every call and a publish run makes
        about twenty-five thousand of them, all with the same timestamp.

        Keyed on `as_of` and dropped by `fit`, because this is precisely where a
        leakage bug would live: a cache that survived a refit would answer a
        walk-forward fold with the previous fold's data, which is the failure
        that killed the 2025 version.
        """
        key = pd.Timestamp(as_of)
        cached = self._visible_cache.get(key)
        if cached is None:
            cached = self._history[self._history["known_at"] <= key]
            self._visible_cache[key] = cached
        return cached

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

    def plain_rate(self, player: str, as_of) -> tuple[float | None, float]:
        """Fouls divided by nineties. No shrinkage, no decay, no adjustment.

        The number the site publishes is the model's expected value for one
        match, which is a different thing and a better one. This exists so the
        two can be shown side by side: where they disagree, the difference IS
        the model's opinion, and a reader is entitled to see how big it is.

        Deliberately not shrunk and not decayed. Shrinking it would pull it
        toward the same prior the model uses and leave nothing to compare.

        Returns (rate, nineties). None when he has never played, rather than a
        zero that reads as "never fouls anyone".
        """
        rows = self._visible(as_of)
        rows = rows[rows["player"] == player]
        if rows.empty:
            return None, 0.0

        nineties = float(rows["minutes"].sum()) / 90.0
        if nineties <= 0:
            return None, 0.0
        return float(rows[self.stat].sum()) / nineties, nineties

    def minutes_profile(self, player: str, as_of, confirmed: str | None = None) -> MinutesProfile:
        """Split minutes into whether he plays and how long, rather than averaging.

        `confirmed` collapses the first stage once an official lineup is known:
        "start", "bench" or "out". Before that it is estimated from how often he
        has recently started, benched and gone unused.
        """
        past = self._visible(as_of)
        rows = past[past["player"] == player].tail(12)

        if rows.empty:
            # An unseen player who is expected to feature. Returning nothing for
            # him is how a promoted club came to show a quarter of Manchester
            # United's fouls, so the honest prior is a typical starter with the
            # uncertainty carried as thin evidence rather than as a low number.
            profile = MinutesProfile(0.70, 0.20, 0.10, self._default_minutes, 22.0, 0.0)
        else:
            w = _weights(rows["known_at"], as_of, self.half_life_days)
            mins = rows["minutes"].to_numpy(dtype=float)
            started = mins >= STARTER_MINUTES
            benched = (mins > 0) & ~started
            unused = mins <= 0

            total = w.sum()
            # A weak prior toward a squad player, so one appearance does not
            # imply certainty in either direction.
            k = 2.0
            p_start = float((w[started].sum() + k * 0.55) / (total + k))
            p_sub = float((w[benched].sum() + k * 0.20) / (total + k))
            p_unused = max(0.0, 1.0 - p_start - p_sub)

            def _avg(mask, fallback):
                if not mask.any():
                    return fallback
                return float(np.average(mins[mask], weights=w[mask]))

            profile = MinutesProfile(
                p_start=p_start,
                p_sub=p_sub,
                p_unused=p_unused,
                minutes_if_start=_avg(started, self._default_minutes),
                minutes_if_sub=_avg(benched, 22.0),
                appearances=float(total),
            )

        if confirmed == "start":
            return MinutesProfile(1.0, 0.0, 0.0, profile.minutes_if_start, profile.minutes_if_sub, profile.appearances)
        if confirmed == "bench":
            # Named on the bench is not the same as playing. Roughly half of
            # named substitutes come on at all.
            return MinutesProfile(0.0, 0.5, 0.5, profile.minutes_if_start, profile.minutes_if_sub, profile.appearances)
        if confirmed == "out":
            return MinutesProfile(0.0, 0.0, 1.0, profile.minutes_if_start, profile.minutes_if_sub, profile.appearances)
        return profile

    MIN_OPPONENT_ROWS = 200

    def opponent_factor(self, opponent: str, as_of) -> float:
        """How many fouls this opponent draws out of teams, relative to league.

        The name is resolved before the lookup, because it was not. Fixtures say
        "Man United" and the history says "Manchester United", so the lookup
        found nothing and returned 1.0, which reads as "this opponent is
        perfectly average" rather than "I could not find this opponent". Around
        half the league was affected in published output, and the discarded
        adjustments were not small: United 0.84, Tottenham 1.25.
        """
        from foulgorithm.identity.teams import history_name

        past = self._visible(as_of)
        resolved = history_name(opponent)
        rows = past[past["opponent"] == resolved]

        if len(rows) < self.MIN_OPPONENT_ROWS:
            # A promoted club has no top-flight history at all, and shrugging at
            # 1.0 is the failure this project is meant not to make. Its second
            # tier record is thin evidence but it is evidence.
            return self._promoted_opponent_factor(opponent)

        w = _weights(rows["known_at"], as_of, self.half_life_days)
        nineties = (rows["minutes"].to_numpy() / 90.0) * w
        rate = float((rows[self.stat].to_numpy() * w).sum() / max(nineties.sum(), 1e-6))
        raw = rate / max(self._league_rate, 1e-6)
        # Pull toward 1 by the character's willingness to trust the matchup.
        return 1.0 + (raw - 1.0) * self.opponent_weight

    def _promoted_opponent_factor(self, opponent: str) -> float:
        """Second-tier evidence for a club with no first-tier record, or 1.0.

        Only the fouls-committed market uses it. The drawn market asks the
        mirrored question and the same number would point the wrong way.
        """
        if self.stat != "fouls_committed":
            return 1.0
        try:
            from foulgorithm.features import promotion

            factor = promotion.opponent_factor(opponent, promotion.current_season())
        except Exception:
            return 1.0
        if factor is None:
            return 1.0
        return 1.0 + (factor - 1.0) * self.opponent_weight

    def _single_distribution(self, mean: float) -> CountDistribution:
        """One negative binomial at the given mean. The old behaviour."""
        mean = max(mean, 0.02)
        return negbin_pmf(mean, mean * self.dispersion_at(mean))

    def _mean_for(self, rate: float, minutes: float, opp: float, referee_factor: float, player: str) -> float:
        mean = rate * (minutes / 90.0) * opp * referee_factor
        if self.amplify != 1.0:
            base = self.prior_rate(player) * (minutes / 90.0)
            mean = base + (mean - base) * self.amplify
        return max(mean, 0.0)

    def predict_one(
        self,
        player: str,
        opponent: str,
        as_of,
        referee_factor: float = 1.0,
        confirmed: str | None = None,
        team: str | None = None,
    ) -> tuple[CountDistribution, dict]:
        rate, effective = self.player_rate(player, as_of)
        profile = self.minutes_profile(player, as_of, confirmed=confirmed)
        opp = self.opponent_factor(opponent, as_of)
        h2h = self.head_to_head_factor(team, opponent) if team else 1.0
        opp *= h2h

        # A mixture over whether he plays, not one distribution at his average
        # minutes. The mean is identical either way, which is why averaging
        # never showed up as a bias. The shape is not, and the shape is what a
        # bet settles on: a rotation risk has a real spike at zero that a single
        # distribution smooths away.
        pmfs, weights = [], []
        for weight, minutes in profile.branches():
            if weight <= 1e-9:
                continue
            weights.append(weight)
            if minutes <= 0.0:
                # He did not play, so he committed nothing. Not a small number.
                pmfs.append(np.array([1.0]))
            else:
                mean = self._mean_for(rate, minutes, opp, referee_factor, player)
                pmfs.append(self._single_distribution(mean).probabilities())

        width = max(len(x) for x in pmfs)
        stacked = np.zeros(width)
        for weight, pmf in zip(weights, pmfs):
            stacked[: len(pmf)] += weight * pmf
        dist = CountDistribution(stacked)

        minutes = profile.mean_minutes()
        return dist, {
            "ratePer90": round(rate, 3),
            "expectedMinutes": round(minutes, 1),
            "expected_fouls": round(dist.mean(), 3),
            "opponentFactor": round(opp, 3),
            "headToHeadFactor": round(h2h, 3),
            "refereeFactor": round(referee_factor, 3),
            "effectiveMatches": round(effective, 1),
            "startProbability": round(profile.p_start, 3),
            "minutesIfStarting": round(profile.minutes_if_start, 1),
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
    "valentina": dict(half_life_days=400, prior_matches=6, opponent_weight=1.6, dispersion=1.05,
                      amplify=1.15, reads_head_to_head=True),
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
