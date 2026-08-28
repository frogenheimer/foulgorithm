"""Six leagues on one scale, so a foreign record counts without misleading.

We hold 485,569 player-matches across England, Spain, Italy, Germany, France
and the USA, and read 81,327 of them. The other five are not simply more rows:
Serie A runs 1.197 fouls per 90 against England's 0.972, a 23% gap, where
England's own eight-season spread is about 9%. Concatenating the files would
overstate every Italian player by a fifth.

`29-why-leagues-differ.md` measured the shape of that gap. It is present in
every position, 16% to 23%, it is not explained by how much each league
tackles, and it holds proportionally across roles with very different base
rates. So the model is one multiplicative intercept per league, and a
league-by-position interaction has to earn its parameters before anyone adds
one.

What this buys, in order: position priors estimated on 5.5x the data, which
sets the floor for every thin player; a record for arrivals from abroad, 16 of
the 35 players the site currently shows blank; and shrinkage constants fitted
across 8,968 players instead of set by hand.

Two refusals, both deliberate. A league with no fitted offset raises rather
than being assumed English, because missing reading as average is the failure
this project is built around. And minutes are never rescaled: the gap is in
what gets whistled, not in how long anyone played.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REFERENCE = "ENG"

#: Below this many ninety-minute equivalents a league's rate is noise, and an
#: offset fitted on noise is worse than leaving the league out.
MIN_NINETIES = 500.0


def league_offsets(
    history: pd.DataFrame,
    stat: str = "fouls_committed",
    reference: str = REFERENCE,
    min_nineties: float = MIN_NINETIES,
) -> dict[str, float]:
    """Each league's rate relative to the reference. Fitted, never assumed.

    Callers inside a walk-forward fold pass only the rows knowable at that
    timestamp: an offset fitted on the whole file would be a leak of exactly
    the kind the harness exists to catch.
    """
    if "league" not in history.columns:
        raise ValueError("cannot fit league offsets on a frame with no league column")

    grouped = history.groupby("league")
    nineties = grouped["minutes"].sum() / 90.0
    rates = grouped[stat].sum() / nineties.replace(0, np.nan)

    if reference not in rates.index or not np.isfinite(rates.get(reference, np.nan)):
        raise ValueError(f"no {reference} rows to fit league offsets against")

    base = float(rates[reference])
    return {
        str(code): float(rate / base)
        for code, rate in rates.items()
        if nineties.get(code, 0.0) >= min_nineties and np.isfinite(rate)
    }


def to_reference(
    history: pd.DataFrame,
    offsets: dict[str, float],
    stats: tuple[str, ...] = ("fouls_committed", "fouls_drawn"),
) -> pd.DataFrame:
    """Rescale foul counts onto the reference league's scale.

    A Serie A player's 1.2 fouls per 90 becomes what the same behaviour would
    be whistled at in England. Minutes are untouched, so exposure stays real
    and only the counts move.
    """
    if "league" not in history.columns:
        raise ValueError("cannot rescale a frame with no league column")

    unknown = sorted(set(history["league"].unique()) - set(offsets))
    if unknown:
        raise ValueError(
            f"no fitted league offset for {', '.join(unknown)}. Treating an "
            "unmapped league as the reference would silently overstate every "
            "player in it."
        )

    out = history.copy()
    factor = out["league"].map(offsets).astype(float)
    for stat in stats:
        if stat in out.columns:
            out[stat] = out[stat] / factor
    return out


def rank_transfer(
    history: pd.DataFrame,
    stat: str = "fouls_committed",
    min_nineties: float = 5.0,
) -> dict:
    """Does a player who changes league keep his rank better than his rate?

    The sharpest test available of whether the league gap is interpretation or
    behaviour. If it is interpretation, a Serie A player's count overstates
    what he would concede in England while his standing among his peers
    transfers intact.

    Returns the rank correlation across movers, plus how much their raw rate
    jumps at the border against how much it jumps once the offset is applied.
    A good offset shrinks the second toward zero.
    """
    offsets = league_offsets(history, stat=stat)
    per_league = (
        history.groupby(["player", "league"])
        .agg(nineties=("minutes", lambda m: m.sum() / 90.0), events=(stat, "sum"))
        .reset_index()
    )
    per_league = per_league[per_league["nineties"] >= min_nineties]
    per_league["rate"] = per_league["events"] / per_league["nineties"]

    # Percentile within each league, so ranks are comparable across them.
    per_league["percentile"] = per_league.groupby("league")["rate"].rank(pct=True)

    movers = per_league.groupby("player").filter(lambda g: g["league"].nunique() > 1)  # noqa: PD101 - counting leagues, not testing constancy
    if movers.empty:
        return {
            "movers": 0,
            "rank_correlation": float("nan"),
            "raw_rate_change": float("nan"),
            "adjusted_rate_change": float("nan"),
        }

    # When each spell started, computed once. Looking it up inside the loop
    # meant refiltering the whole history per mover per league, which is a
    # billion row comparisons on the real file.
    started = history.groupby(["player", "league"])["kickoff_utc"].min()

    before, after, raw, adjusted = [], [], [], []
    for player, group in movers.groupby("player"):
        # Order by when each spell happened, so "before" and "after" mean it.
        spells = sorted(
            (started.get((player, row.league)), row.league, float(row.rate), float(row.percentile))
            for row in group.itertuples()
        )
        (_, league_a, rate_a, pct_a), (_, league_b, rate_b, pct_b) = spells[0], spells[-1]

        before.append(pct_a)
        after.append(pct_b)
        raw.append(rate_b - rate_a)
        adjusted.append(rate_b / offsets.get(league_b, 1.0) - rate_a / offsets.get(league_a, 1.0))

    correlation = (
        float(pd.Series(before).corr(pd.Series(after))) if len(before) > 1 else float("nan")
    )
    return {
        "movers": len(before),
        "rank_correlation": correlation,
        "raw_rate_change": float(np.mean(raw)),
        "adjusted_rate_change": float(np.mean(adjusted)),
        "offsets": offsets,
    }
