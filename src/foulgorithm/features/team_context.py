"""Opponent and referee factors from the match store, which is current.

The player model's context factors read the player-match archive, which froze
in September 2025: a live prediction was reading a frozen file for two of its
three inputs. The match store holds the same quantities, team level, current
through the latest round, and `match_features` already computes them with
shrinkage and decay for the match models. This adapter points the player
model at that machinery.

Two things matter and both are ratios:

- **Direction.** For fouls COMMITTED, the opponent's relevant property is how
  many fouls sides give away against them, the `drawn` side of the match
  context. For fouls DRAWN it is how many the opponent commits. Getting this
  backwards is the conceptual bug advisor 2 warned about by name.
- **Provider safety.** The match store counts fouls a little differently from
  the player archive, but every factor here is a ratio to the same store's
  league average, so the provider's counting convention cancels. No offset
  applies to a ratio taken inside one source.

Name spaces: the store spells clubs as football-data does. Anything arriving
in archive spelling is mapped through the existing crosswalk, and an unknown
club simply has no rows, which the shrinkage turns into the prior rather than
into a silent 1.0: the factor is 1.0 BECAUSE the prior says so, with its
effective-match count carried alongside, never because a lookup failed.
"""

from __future__ import annotations

import pandas as pd

# The shared implementations. Deliberately the same functions the match models
# use, so the player and match layers cannot drift apart on what a factor means.
from foulgorithm.features import match_features as mf
from foulgorithm.identity.teams import HISTORY_TO_FIXTURE


def fixture_name(team: str) -> str:
    """The club as the match store spells it. Identity when they agree."""
    return HISTORY_TO_FIXTURE.get(team, team)


class MatchContextSource:
    """Context factors for the player model, computed from match data.

    As-of aware throughout: every factor is built from rows knowable at the
    prediction timestamp, so one source instance can serve a whole
    walk-forward run without leaking.
    """

    def __init__(
        self,
        matches: pd.DataFrame,
        half_life_days: float = mf.DEFAULT_HALF_LIFE_DAYS,
        prior_matches: float = mf.DEFAULT_PRIOR_MATCHES,
        referee_prior: float = mf.DEFAULT_REFEREE_PRIOR,
    ):
        self._matches = matches
        self.half_life_days = half_life_days
        self.prior_matches = prior_matches
        self.referee_prior = referee_prior
        self._cache: dict = {}

    def _at(self, as_of):
        key = pd.Timestamp(as_of)
        held = self._cache.get(key)
        if held is None:
            past = mf.visible(self._matches, key)
            w = mf._weights(past["known_at"], key, self.half_life_days)
            league = float((past["total_fouls"].to_numpy(dtype=float) * w).sum() / w.sum())
            held = (past, w, league)
            self._cache[key] = held
        return held

    def opponent_factor(self, opponent: str, as_of, market: str) -> tuple[float, float]:
        """(raw factor, effective matches). Above 1.0 means a busier fixture.

        The factor is the DEVIATION source; the character's opponent weight is
        applied by the model, not here, so five characters can disagree about
        one measurement rather than measuring five times.
        """
        past, w, league = self._at(as_of)
        side = league / 2.0
        kind = "drawn" if market.endswith("committed") else "commit"
        shrunk, effective = mf._team_rate(
            past, w, fixture_name(opponent), kind, side, self.prior_matches
        )
        return shrunk / side, effective

    def referee_factor(self, referee: str | None, as_of) -> tuple[float, float]:
        past, w, league = self._at(as_of)
        return mf._referee_factor(past, w, referee, league, self.referee_prior)
