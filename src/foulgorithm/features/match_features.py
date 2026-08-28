"""Match-level features, built as of a timestamp.

Every function here takes `as_of` and may only use rows whose `known_at` is at
or before it. That is the whole leakage defence, and it is why models never
touch the store directly.

A note on what is and is not a feature: possession, shots and corners are match
OUTCOMES. You do not know a game's shot count before it kicks off. They enter
the model only as a team's historical average, never as the current match's
value. Treating them otherwise is exactly the leak that made the 2025 backtest
meaningless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# How fast old matches stop counting. One year to halve is a reasonable start
# and the backtest tunes it. Fouls per match fell 19.6% across the sample, so
# treating 2004 as equal evidence to 2025 would be plainly wrong.
DEFAULT_HALF_LIFE_DAYS = 400.0

# Prior strength, in effective matches. A team with few matches gets pulled
# toward the league mean. This is the shrinkage the 2025 version lacked.
DEFAULT_PRIOR_MATCHES = 8.0
DEFAULT_REFEREE_PRIOR = 15.0


@dataclass
class MatchContext:
    """Everything known about a fixture before kickoff."""

    league_fouls: float
    home_commit: float
    away_commit: float
    home_drawn: float
    away_drawn: float
    referee_factor: float
    mismatch: float
    home_matches: float
    away_matches: float
    referee_matches: float


def visible(history: pd.DataFrame, as_of) -> pd.DataFrame:
    """Rows knowable at `as_of`. The single most important line in the codebase."""
    return history[history["known_at"] <= as_of]


def _weights(known_at: pd.Series, as_of, half_life_days: float) -> np.ndarray:
    age_days = (pd.Timestamp(as_of) - known_at).dt.total_seconds().to_numpy() / 86400.0
    return np.power(0.5, np.maximum(age_days, 0.0) / half_life_days)


def build_context(
    history: pd.DataFrame,
    home: str,
    away: str,
    referee: str | None,
    as_of,
    odds: tuple[float | None, float | None, float | None] = (None, None, None),
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    prior_matches: float = DEFAULT_PRIOR_MATCHES,
    referee_prior: float = DEFAULT_REFEREE_PRIOR,
) -> MatchContext:
    past = visible(history, as_of)
    if past.empty:
        raise ValueError("no history visible at as_of")

    w = _weights(past["known_at"], as_of, half_life_days)
    league_total = float(np.average(past["total_fouls"].to_numpy(dtype=float), weights=w))
    league_side = league_total / 2.0

    home_commit, home_n = _team_rate(past, w, home, "commit", league_side, prior_matches)
    away_commit, away_n = _team_rate(past, w, away, "commit", league_side, prior_matches)
    home_drawn, _ = _team_rate(past, w, home, "drawn", league_side, prior_matches)
    away_drawn, _ = _team_rate(past, w, away, "drawn", league_side, prior_matches)

    ref_factor, ref_n = _referee_factor(past, w, referee, league_total, referee_prior)

    return MatchContext(
        league_fouls=league_total,
        home_commit=home_commit / league_side,
        away_commit=away_commit / league_side,
        home_drawn=home_drawn / league_side,
        away_drawn=away_drawn / league_side,
        referee_factor=ref_factor,
        mismatch=mismatch_from_odds(*odds),
        home_matches=home_n,
        away_matches=away_n,
        referee_matches=ref_n,
    )


def _team_rate(
    past: pd.DataFrame,
    w: np.ndarray,
    team: str,
    kind: str,
    league_side: float,
    prior_matches: float,
) -> tuple[float, float]:
    """Weighted, shrunk per-match rate for one team.

    `commit` is fouls the team gave away. `drawn` is fouls given away against
    them. A team appears as both home and away, and both count.
    """
    at_home = past["home_team_raw"].to_numpy() == team
    at_away = past["away_team_raw"].to_numpy() == team
    if not (at_home.any() or at_away.any()):
        return league_side, 0.0

    if kind == "commit":
        values = np.where(at_home, past["home_fouls"], past["away_fouls"]).astype(float)
    else:
        values = np.where(at_home, past["away_fouls"], past["home_fouls"]).astype(float)

    mask = at_home | at_away
    weights = w[mask]
    observed = values[mask]
    effective_n = float(weights.sum())

    # Empirical Bayes: pull toward the league mean in proportion to how little
    # we know. A promoted club with no history lands exactly on the prior.
    shrunk = (float((weights * observed).sum()) + prior_matches * league_side) / (
        effective_n + prior_matches
    )
    return shrunk, effective_n


def _referee_factor(
    past: pd.DataFrame,
    w: np.ndarray,
    referee: str | None,
    league_total: float,
    prior: float,
) -> tuple[float, float]:
    """Shrunk referee multiplier, relative to the league.

    Still a raw ratio and therefore still confounded by fixture assignment. It
    is shrunk hard so a referee with few matches barely moves the number, which
    is the minimum fix. Estimating referee and team effects jointly is the
    proper answer and belongs in the GLM.
    """
    if not referee:
        return 1.0, 0.0
    mask = (past["referee_raw"] == referee).to_numpy()
    if not mask.any():
        return 1.0, 0.0

    weights = w[mask]
    observed = past["total_fouls"].to_numpy(dtype=float)[mask]
    effective_n = float(weights.sum())
    shrunk = (float((weights * observed).sum()) + prior * league_total) / (effective_n + prior)
    return shrunk / league_total, effective_n


def mismatch_from_odds(home: float | None, draw: float | None, away: float | None) -> float:
    """How lopsided the fixture is, from 0 (even) to about 1 (walkover).

    Derived from the closing 1X2 prices with the bookmaker margin removed. The
    market prices a mismatch better than any rating we would build, and a heavy
    underdog spends the match defending, which is when fouls happen.
    """
    if not home or not draw or not away:
        return 0.0
    raw = np.array([1 / home, 1 / draw, 1 / away], dtype=float)
    probs = raw / raw.sum()  # strip the overround
    return float(abs(probs[0] - probs[2]))
