"""One model per character.

These are genuinely different models, not one model with five parameter sets.
Each reads the evidence in a way its temperament would, using different
features, different memory and different confidence.

The constraint that keeps this honest: a character may be wrong, but never
deliberately stupid. Every mechanism below is a position a real analyst could
defend, so the bake-off is real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from foulgorithm.characters import base as characters
from foulgorithm.features import match_features as mf
from foulgorithm.models.base import CountDistribution, register
from foulgorithm.models.match_models import _MatchModel, negbin_pmf


class _CharacterModel(_MatchModel):
    """Shared plumbing. Each subclass supplies its own `_mean`."""

    character_id: str

    @property
    def character(self) -> characters.Character:
        return characters.get(self.character_id)


@register
class AlanAnger(_CharacterModel):
    """Anger has no memory for context and total recall for the latest offence.

    A 60 day half-life means roughly the last two months carry the weight.
    Shrinkage is near-absent because averages feel like excuses. Deviations from
    the league mean are then AMPLIFIED: if a side has been fouling more than
    usual, Alan assumes they have become that team rather than that they had a
    run of it. The narrow dispersion is overconfidence, and it is deliberate.
    """

    id = "alan_anger"
    version = "1.0.0"
    character_id = "alan"

    AMPLIFY = 1.35

    def __init__(self, **kwargs):
        kwargs.setdefault("half_life_days", 60.0)
        kwargs.setdefault("dispersion_scale", 0.5)
        kwargs.setdefault("label", "alan_anger")
        super().__init__(**kwargs)

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
            prior_matches=1.5,
            referee_prior=4.0,
        )
        side = ctx.league_fouls / 2.0
        home = np.sqrt(ctx.home_commit * ctx.away_drawn)
        away = np.sqrt(ctx.away_commit * ctx.home_drawn)
        # Push every deviation further from 1. Anger does not do "slightly".
        home = 1.0 + (home - 1.0) * self.AMPLIFY
        away = 1.0 + (away - 1.0) * self.AMPLIFY
        referee = 1.0 + (ctx.referee_factor - 1.0) * self.AMPLIFY
        return side * (home + away) * referee


@register
class LilyLust(_CharacterModel):
    """Lust wants the beautiful thing, not the sensible one.

    Two mechanisms. A very long memory, because reputations stay seductive long
    after they stop being true, so Lily prices clubs on who they were. And a
    glamour weighting: the more storied the fixture, the more she expects to
    happen in it, nudged toward the over.

    Glamour is proxied by how long each club has been in this league, which is
    crude but defensible and needs no data we do not hold.
    """

    id = "lily_lust"
    version = "1.0.0"
    character_id = "lily"

    GLAMOUR_PULL = 0.05

    def __init__(self, **kwargs):
        kwargs.setdefault("half_life_days", 1400.0)
        kwargs.setdefault("dispersion_scale", 0.8)
        kwargs.setdefault("label", "lily_lust")
        super().__init__(**kwargs)
        self._glamour: dict[str, float] = {}

    def fit(self, train: pd.DataFrame) -> None:
        super().fit(train)
        appearances = pd.concat([train["home_team_raw"], train["away_team_raw"]]).value_counts()
        top = appearances.max()
        self._glamour = {team: float(n) / float(top) for team, n in appearances.items()}

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        base = side * np.sqrt(ctx.home_commit * ctx.away_drawn) + side * np.sqrt(
            ctx.away_commit * ctx.home_drawn
        )
        glamour = (
            self._glamour.get(row["home_team_raw"], 0.5)
            + self._glamour.get(row["away_team_raw"], 0.5)
        ) / 2.0
        return base * ctx.referee_factor * (1.0 + self.GLAMOUR_PULL * glamour)


@register
class ValentinaViolence(_CharacterModel):
    """Violence looks for conflict and finds it.

    Valentina reads a fixture's temperature from its discipline record: how
    often these sides get booked, relative to the league. That aggression factor
    then bends a foul-rate estimate up or down.

    Her first version modelled cards alone and converted to fouls with a fitted
    ratio. It finished WORSE than predicting the league average, at 0.6505 log
    loss against 0.5993, because cards are a noisy proxy that has been drifting
    away from fouls for two decades. The finding stands and is recorded in
    docs/modelling-log.md. This version keeps her lens, aggression drives the
    prediction, without throwing away the obvious evidence, which is what a
    competent analyst with her temperament would actually do.
    """

    id = "valentina_violence"
    version = "2.0.0"
    character_id = "valentina"

    #: How hard the aggression reading bends the estimate. Her whole character
    #: sits in this number: 0 would make her the champion, 1 would make her the
    #: failed v1.
    AGGRESSION_PULL = 0.45

    def __init__(self, **kwargs):
        kwargs.setdefault("half_life_days", 420.0)
        kwargs.setdefault("dispersion_scale", 0.7)
        kwargs.setdefault("label", "valentina_violence")
        super().__init__(**kwargs)

    def _card_rate(self, team: str, as_of, past: pd.DataFrame, w: np.ndarray) -> float:
        at_home = past["home_team_raw"].to_numpy() == team
        at_away = past["away_team_raw"].to_numpy() == team
        mask = at_home | at_away
        if not mask.any():
            return float("nan")
        own = np.where(
            at_home,
            past["home_yellows"].fillna(0) + past["home_reds"].fillna(0),
            past["away_yellows"].fillna(0) + past["away_reds"].fillna(0),
        ).astype(float)
        return float(np.average(own[mask], weights=w[mask]))

    def _aggression(self, row: pd.Series) -> float:
        """How hot these two sides run on discipline, relative to the league.

        1.0 means an ordinary fixture. Above 1.0 means both sides collect more
        cards than average, which Valentina reads as a fight waiting to happen.
        """
        past = mf.visible(self._history, row["kickoff_utc"])
        w = np.power(
            0.5,
            (pd.Timestamp(row["kickoff_utc"]) - past["known_at"]).dt.total_seconds().to_numpy()
            / 86400.0
            / self.half_life_days,
        )
        league_cards = float(
            np.average(
                (
                    past["home_yellows"].fillna(0)
                    + past["away_yellows"].fillna(0)
                    + past["home_reds"].fillna(0)
                    + past["away_reds"].fillna(0)
                ).to_numpy(dtype=float),
                weights=w,
            )
        )
        if league_cards <= 0:
            return 1.0

        home = self._card_rate(row["home_team_raw"], row["kickoff_utc"], past, w)
        away = self._card_rate(row["away_team_raw"], row["kickoff_utc"], past, w)
        # An unseen club is assumed ordinary rather than assumed placid.
        home = league_cards / 2.0 if np.isnan(home) else home
        away = league_cards / 2.0 if np.isnan(away) else away
        return float((home + away) / league_cards)

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
        )
        side = ctx.league_fouls / 2.0
        base = (
            side * np.sqrt(ctx.home_commit * ctx.away_drawn)
            + side * np.sqrt(ctx.away_commit * ctx.home_drawn)
        ) * ctx.referee_factor

        # Bend toward the aggression reading rather than replacing the estimate
        # with it. Keeps her lens without discarding the evidence.
        heat = 1.0 + (self._aggression(row) - 1.0) * self.AGGRESSION_PULL
        return base * heat


@register
class TaylerTerror(_CharacterModel):
    """Terror assumes the worst and hedges accordingly.

    A very long memory so no single result can move him, enormous shrinkage so
    every team sits close to the league average, and a wide distribution because
    a narrow one might be wrong.

    Tayler will be the best calibrated of the five and among the least useful,
    because a prediction indistinguishable from the average is barely a
    prediction. His confidence floor lives in selection, not here: the model
    still produces a number, he just declines to bet on most of them.
    """

    id = "tayler_terror"
    version = "1.0.0"
    character_id = "tayler"

    def __init__(self, **kwargs):
        kwargs.setdefault("half_life_days", 1100.0)
        kwargs.setdefault("dispersion_scale", 1.15)
        kwargs.setdefault("label", "tayler_terror")
        super().__init__(**kwargs)

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
            prior_matches=45.0,
            referee_prior=60.0,
        )
        side = ctx.league_fouls / 2.0
        return side * np.sqrt(ctx.home_commit * ctx.away_drawn) + side * np.sqrt(
            ctx.away_commit * ctx.home_drawn
        )


@register
class BdogBravery(_CharacterModel):
    """Bravery is willing to be alone.

    Bdog fits the other four, takes their consensus, and shades deliberately
    away from it. The argument is that a crowd agreeing is a crowd that has
    already priced the obvious, so whatever is left sits on the other side.

    He also trusts thin evidence the others shrink away, because someone has to
    be first on a genuinely changed team.

    Costs four extra fits per refit. Worth it: this is the only character whose
    view depends on what the others think.
    """

    id = "bdog_bravery"
    version = "1.0.0"
    character_id = "bdog"

    FADE = 0.4

    def __init__(self, **kwargs):
        kwargs.setdefault("half_life_days", 260.0)
        kwargs.setdefault("dispersion_scale", 0.7)
        kwargs.setdefault("label", "bdog_bravery")
        super().__init__(**kwargs)
        self._peers: list[_CharacterModel] = []

    def fit(self, train: pd.DataFrame) -> None:
        super().fit(train)
        self._peers = [AlanAnger(), LilyLust(), ValentinaViolence(), TaylerTerror()]
        for peer in self._peers:
            peer.fit(train)

    def _mean(self, row: pd.Series) -> float:
        ctx = mf.build_context(
            self._history,
            row["home_team_raw"],
            row["away_team_raw"],
            row.get("referee_raw"),
            row["kickoff_utc"],
            half_life_days=self.half_life_days,
            prior_matches=3.0,
        )
        side = ctx.league_fouls / 2.0
        own = (
            side * np.sqrt(ctx.home_commit * ctx.away_drawn)
            + side * np.sqrt(ctx.away_commit * ctx.home_drawn)
        ) * ctx.referee_factor

        peer_means = [p._mean(row) for p in self._peers]
        if not peer_means:
            return own
        consensus = float(np.mean(peer_means))
        # Step away from the crowd, from his own starting point.
        return own + (own - consensus) * self.FADE


def character_models() -> list[type]:
    """The five, in a stable order for reporting."""
    return [AlanAnger, LilyLust, ValentinaViolence, TaylerTerror, BdogBravery]


def build_all() -> list[_CharacterModel]:
    return [cls() for cls in character_models()]


def predict_all(history: pd.DataFrame, fixtures: pd.DataFrame) -> dict[str, list[CountDistribution]]:
    """Fit and predict every character on the same data. Equal effort, same pool."""
    out: dict[str, list[CountDistribution]] = {}
    for model in build_all():
        model.fit(history)
        out[model.character_id] = model.predict(fixtures)
    return out
