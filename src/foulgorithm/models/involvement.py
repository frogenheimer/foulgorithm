"""Foul involvements: fouls committed plus fouls won, as one distribution.

Asked for because it is how people actually watch a player. A holding midfielder
who commits two and wins two was in four incidents, and two separate tables
showing "2" each never say that.

**Independence looked wrong and is right.** Fouls committed and fouls won
correlate at +0.135 across 59,649 player-matches, and the variance of their sum
runs 13.5% above what independence predicts, so the convolution was widened to
match. Backtested over 5,761 player-matches, widening made it WORSE: log loss
0.4615 to 0.4626, calibration error 0.0115 to 0.0180.

The reason is the same mistake made once already on the player dispersion, and
worth naming so it is not made a third time. **That 13.5% is population variance,
not residual variance.** It includes the spread BETWEEN players, which the model
already knows about, because it predicts each player from his own rate. What is
left over after that is close to independent.

The plain convolution tracks reality well at every line: 0.769 predicted against
0.752 observed at 0.5, 0.293 against 0.282 at 2.5. Widening pushed the low line
down past the truth and the high lines up past it. `widen` therefore defaults to
1.0 and is kept only so the finding can be re-tested.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from foulgorithm.models.base import CountDistribution

# Measured, and measured to be the wrong correction. See the module docstring:
# this is population variance and the model already accounts for most of it.
# Kept as a named number so the negative result stays visible rather than
# looking like a parameter nobody tried.
DISPERSION_INFLATION = 1.135

# What actually ships. Independence, because it scored better.
DEFAULT_WIDEN = 1.0

MIN_MINUTES = 60


def combine(
    committed: CountDistribution,
    drawn: CountDistribution,
    widen: float = DEFAULT_WIDEN,
) -> CountDistribution:
    """Total foul involvements.

    `widen` is a variance ratio, not a standard deviation ratio. Below 1.0 this
    raises: narrowing would claim more precision than either input had.
    """
    if widen < 1.0:
        raise ValueError(
            f"widen={widen} would narrow the result below its own inputs, which "
            "claims precision neither distribution had"
        )

    a, b = committed.probabilities(), drawn.probabilities()
    joint = np.convolve(a, b)
    if widen == 1.0:
        return CountDistribution(joint)

    k = np.arange(len(joint))
    mean = float((joint * k).sum())
    var = float((joint * (k - mean) ** 2).sum())
    if var <= 0:
        return CountDistribution(joint)

    # Spread each point mass around the mean by the factor that takes the
    # variance to its measured value, then re-bin. Scaling about the mean is
    # what keeps the centre fixed.
    scale = float(np.sqrt(widen))
    moved = mean + (k - mean) * scale

    out = np.zeros(len(joint) + int(np.ceil(moved.max() - k.max())) + 1)
    for weight, position in zip(joint, moved, strict=False):
        if weight <= 0:
            continue
        position = max(position, 0.0)
        low = int(np.floor(position))
        frac = position - low
        out[low] += weight * (1 - frac)
        if low + 1 < len(out):
            out[low + 1] += weight * frac

    # Re-binning at the zero floor loses a little of the mean. Put it back by
    # moving weight between the first two bins rather than rescaling, which
    # would change the shape everywhere to fix an error in one place.
    result = CountDistribution(out)
    drift = mean - result.mean()
    if abs(drift) > 1e-9 and len(out) > 1:
        adjusted = out.copy()
        shift = min(max(drift * adjusted.sum(), -adjusted[1]), adjusted[0])
        adjusted[0] -= shift
        adjusted[1] += shift
        result = CountDistribution(np.clip(adjusted, 0, None))
    return result


@lru_cache(maxsize=1)
def dispersion_inflation() -> float:
    """Re-derive the widening factor from history. Used by the test, not at build time."""
    from foulgorithm.store.players import load_player_matches

    d = load_player_matches()
    d = d[d["minutes"] >= MIN_MINUTES]
    c = d["fouls_committed"].to_numpy(dtype=float)
    w = d["fouls_drawn"].to_numpy(dtype=float)
    independent = c.var() + w.var()
    return float((c + w).var() / independent) if independent > 0 else 1.0
