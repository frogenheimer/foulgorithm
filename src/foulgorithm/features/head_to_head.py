"""Whether two specific clubs produce more fouls than their own rates imply.

This is Valentina's method, and it exists so that she has one. She is described
as the character who reads the matchup, and what that meant until now was an
opponent weight of 1.6: the same calculation everyone else runs with one number
turned up. Turning a dial is not a different way of thinking about a match.

**The effect is real and small, and both halves of that matter.** Across 9,120
matches and 428 pairings with eight or more meetings, splitting each pairing's
history in half and correlating the halves gives +0.138. The spread of pairing
means is 2.17 fouls where noise alone would produce 1.90, so the true pairing
effect is about 1.06 fouls on a base near 21. Roughly 5%.

A split-half correlation of 0.138 is a reliability near 0.24 by Spearman-Brown,
so roughly three quarters of any pairing residual we observe is noise. Using it
raw would repeat the mistake made with promoted clubs, where a Championship rate
taken at face value scored 16% WORSE than the plain league average and only
helped once shrunk to 37% of itself.
"""

from __future__ import annotations

import statistics

# Measured, not chosen. Spearman-Brown on a split-half correlation of 0.138:
# 2r / (1 + r). Re-derived by backtest/head_to_head_study.py.
SPLIT_HALF = 0.138
RELIABILITY = 2 * SPLIT_HALF / (1 + SPLIT_HALF)

# Typical total fouls in a match, used to turn a residual in fouls into a
# multiplier the player models can apply.
LEAGUE_TOTAL = 21.0

# A pairing needs meetings before its mean means anything. This is the k in a
# standard shrink-toward-nothing weight, n / (n + k), and it is deliberately
# large: at k = 6 a pairing needs six meetings to earn half its own signal.
PRIOR_MEETINGS = 6.0


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Order-independent, because a fixture is the same pairing at either ground.

    Keying on home and away would halve every sample and double the noise in a
    signal that is mostly noise already.
    """
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def adjustment(home: str, away: str, residuals: dict[tuple[str, str], list[float]]) -> float:
    """A multiplier on expected fouls for this fixture.

    `residuals` maps a pairing to its past matches' fouls above or below what
    the two clubs' own rates implied. Returns 1.0 for a pairing never seen,
    which is an absence rather than a claim of average.
    """
    seen = residuals.get(pair_key(home, away))
    if not seen:
        return 1.0

    n = len(seen)
    # Two shrinkages, and both are earned. The first is for sample size, the
    # second is the measured ceiling on how much of this signal is ever real.
    weight = (n / (n + PRIOR_MEETINGS)) * RELIABILITY
    return 1.0 + (statistics.fmean(seen) / LEAGUE_TOTAL) * weight


def residuals_from(matches, as_of=None) -> dict[tuple[str, str], list[float]]:
    """Build the pairing table from match history, honouring an as-of cutoff.

    `matches` is a frame with home_team_raw, away_team_raw, home_fouls,
    away_fouls, known_at. A pairing's residual is the match total minus what the
    two clubs' rates over the same window imply, so a pairing only looks hot if
    it runs hot for reasons neither club carries into its other fixtures.
    """

    if as_of is not None:
        matches = matches[matches["known_at"] <= as_of]
    if matches.empty:
        return {}

    total = matches["home_fouls"].astype(float) + matches["away_fouls"].astype(float)
    matches = matches.assign(total_fouls=total).dropna(subset=["total_fouls"])
    if matches.empty:
        return {}

    league = float(matches["total_fouls"].mean())
    rate: dict[str, float] = {}
    for club in set(matches["home_team_raw"]) | set(matches["away_team_raw"]):
        played = matches[(matches["home_team_raw"] == club) | (matches["away_team_raw"] == club)]
        if len(played) >= 5:
            rate[club] = float(played["total_fouls"].mean())

    out: dict[tuple[str, str], list[float]] = {}
    for r in matches.itertuples():
        h, a = r.home_team_raw, r.away_team_raw
        if h not in rate or a not in rate:
            continue
        expected = rate[h] + rate[a] - league
        out.setdefault(pair_key(h, a), []).append(float(r.total_fouls) - expected)
    return out
