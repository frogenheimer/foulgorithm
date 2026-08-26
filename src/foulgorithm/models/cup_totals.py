"""Expected total fouls in a cup tie, including across the two divisions.

This is the ONLY model number a tie involving a Championship club may publish.
No player-level foul data exists for the second tier at any price, so a player
pick there would be a positional prior wearing a probability. A match total is
a different quantity: total fouls is a team fact, football-data covers E0 and
E1 alike back to 2001, and `features/promotion` already measured the bridge
between them at beta 0.373 over 66 promotions.

**The failure this exists to prevent.** `match_features._team_rate` returns the
league average for a club with no rows in the history, so an unadjusted model
hands Wrexham exactly average Premier League behaviour and publishes that as a
read on Wrexham. Silently average is the mistake this project is meant not to
make. A second-tier club's own record is shrunk onto the top-flight scale
instead, and where even that is missing the tie says so rather than quietly
pricing off the mean.

Only the deviation crosses, never the level. Carrying a Championship club's
raw rate across scores 16% WORSE than using the league average, which is
counter-intuitive precisely because the two divisions' means are almost
identical. See features/promotion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from foulgorithm.features import match_features as mf
from foulgorithm.features import promotion
from foulgorithm.identity.teams import has_player_data, holds_data
from foulgorithm.models.match_models import TeamRatesReferee


class CupTotal(TeamRatesReferee):
    """TeamRatesReferee, with second-tier clubs put on the top-flight scale.

    A tie between two Premier League clubs is a league game and is left exactly
    alone: it produces the champion model's number, to the decimal.
    """

    id = "cup_total"
    version = "1.0.0"

    def __init__(self, priors=promotion, **kwargs):
        super().__init__(**kwargs)
        self._priors = priors

    def _needs_bridge(self, club: str) -> bool:
        """A club we hold, in the division the match history does not cover."""
        return holds_data(club) and not has_player_data(club)

    def context(self, row: pd.Series) -> mf.MatchContext:
        """The fixture's context, with second-tier sides re-scaled."""
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        if side <= 0:
            return ctx

        for club, commit, drawn, matches in (
            (row["home_team_raw"], "home_commit", "home_drawn", "home_matches"),
            (row["away_team_raw"], "away_commit", "away_drawn", "away_matches"),
        ):
            if not self._needs_bridge(club):
                continue
            committed = self._priors.second_tier_prior(club, kind=promotion.COMMITTED)
            if committed is not None:
                setattr(ctx, commit, committed / side)
            drew = self._priors.second_tier_prior(club, kind=promotion.DRAWN)
            if drew is not None:
                setattr(ctx, drawn, drew / side)
            # The club's own record is now doing the work, so the effective
            # match count from a history that never held them is misleading.
            # Report it as unknown rather than as zero-and-therefore-average.
            if committed is not None:
                setattr(ctx, matches, float("nan"))
        return ctx

    def unknown(self, row: pd.Series) -> list[str]:
        """Clubs in this tie we could not price at all. Published, not hidden.

        A second-tier club with no measurable season falls back to the league
        mean, which is the honest floor, but the page has to say that is what
        happened or the number reads as a read on the club.
        """
        out = []
        for club in (row["home_team_raw"], row["away_team_raw"]):
            if self._needs_bridge(club):
                if self._priors.second_tier_prior(club, kind=promotion.COMMITTED) is None:
                    out.append(club)
        return out

    def _mean(self, row: pd.Series) -> float:
        ctx = self.context(row)
        side = ctx.league_fouls / 2.0
        base = side * np.sqrt(ctx.home_commit * ctx.away_drawn) + side * np.sqrt(
            ctx.away_commit * ctx.home_drawn
        )
        return base * ctx.referee_factor
