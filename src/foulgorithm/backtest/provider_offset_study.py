"""How differently the two providers count fouls, measured in the form it takes.

The league API reads about 4.6% above the FBref archive at league level, every
season, never once lower (docs/28-foul-data-sources.md). Both external reviews
made the same demand before that number corrects anything: establish the FORM
of the gap. A multiplicative gap scales every player proportionally; an
additive one adds a flat amount per 90 and a scalar correction would then
inflate the high-volume tail, which is exactly where lines are priced.

This study joins the two providers player by player through the identity
rules, never by raw name, and answers: how big, in what form, and is it stable
across seasons, positions and player volume. The result is written to
`data/reference/provider_offset.json` so the C1 blend applies a measured
artefact with provenance rather than a constant typed from memory.

Run with:

    python -m foulgorithm.backtest.provider_offset_study
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from foulgorithm.identity.players import resolve_names

REFERENCE = Path("data/reference/provider_offset.json")

#: Minutes disagreeing by more than this share mean the two rows do not
#: describe the same exposure, whichever provider is right about it.
MINUTES_TOLERANCE = 0.05


def season_end_year(label: str) -> int:
    """'2023/24' -> 2024, matching the archive's Season_End_Year."""
    return int(str(label)[:4]) + 1


def season_label(end_year: int) -> str:
    """2024 -> '2023/24', the league API's naming."""
    return f"{end_year - 1}/{str(end_year)[2:]}"


def pair(api: pd.DataFrame, archive: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per player per season present in BOTH providers.

    Identity goes through `resolve_names`, never a raw join. An API player who
    does not resolve is counted out, not defaulted: a pair we are not sure of
    is worse than no pair.
    """
    api = api[pd.to_numeric(api["fouls"], errors="coerce").notna()].copy()
    api["season_end"] = api["season"].map(season_end_year)

    arch = archive.groupby(["player", "season"], as_index=False).agg(
        arch_minutes=("minutes", "sum"),
        arch_fouls=("fouls_committed", "sum"),
        position=("position", lambda s: s.dropna().astype(str).mode().iloc[0] if s.notna().any() else ""),
    )

    overlap_seasons = set(arch["season"].unique())
    api = api[api["season_end"].isin(overlap_seasons)]

    resolution = resolve_names(sorted(api["player"].unique()), arch["player"].unique())
    api["resolved"] = api["player"].map(resolution.matched)

    joined = api.dropna(subset=["resolved"]).merge(
        arch,
        left_on=["resolved", "season_end"],
        right_on=["player", "season"],
        suffixes=("_api", ""),
    )

    matched = pd.DataFrame(
        {
            "player": joined["resolved"],
            "season": joined["season_end"],
            "api_minutes": pd.to_numeric(joined["mins_played"], errors="coerce"),
            "api_fouls": pd.to_numeric(joined["fouls"], errors="coerce"),
            "arch_minutes": joined["arch_minutes"].astype(float),
            "arch_fouls": joined["arch_fouls"].astype(float),
            "position": joined["position"],
        }
    ).dropna(subset=["api_minutes", "api_fouls", "arch_minutes", "arch_fouls"])

    gap = (matched["api_minutes"] - matched["arch_minutes"]).abs()
    matched["comparable"] = gap <= MINUTES_TOLERANCE * matched["arch_minutes"]

    report = {
        "pairs": int(len(matched)),
        "unmatched_api": int(len(resolution.unmatched)),
        "ambiguous_api": int(len(resolution.ambiguous)),
        "minutes_disagree": int((~matched["comparable"]).sum()),
    }
    return matched, report


def league_table(matched: pd.DataFrame) -> pd.DataFrame:
    """Per-season rate ratio, api over archive, on comparable pairs."""
    rows = []
    usable = matched[matched["comparable"]]
    for season, group in usable.groupby("season"):
        api_rate = group["api_fouls"].sum() / (group["api_minutes"].sum() / 90.0)
        arch_rate = group["arch_fouls"].sum() / (group["arch_minutes"].sum() / 90.0)
        rows.append(
            {
                "season": season,
                "n": len(group),
                "api_rate": round(float(api_rate), 4),
                "arch_rate": round(float(arch_rate), 4),
                "ratio": round(float(api_rate / arch_rate), 4),
            }
        )
    return pd.DataFrame(rows).sort_values("season").reset_index(drop=True)


def form_fit(matched: pd.DataFrame) -> dict:
    """Multiplicative against additive, decided by residuals, not by taste.

    Multiplicative: api = a x archive, least squares through the origin.
    Additive: api = archive + b x nineties. Whichever leaves the smaller
    residual is the form the correction takes.
    """
    usable = matched[matched["comparable"]]
    x = usable["arch_fouls"].to_numpy(dtype=float)
    y = usable["api_fouls"].to_numpy(dtype=float)
    n90 = usable["arch_minutes"].to_numpy(dtype=float) / 90.0

    a = float((x * y).sum() / (x * x).sum())
    b = float(((y - x) * n90).sum() / (n90 * n90).sum())

    rmse_mult = float(np.sqrt(np.mean((y - a * x) ** 2)))
    rmse_add = float(np.sqrt(np.mean((y - x - b * n90) ** 2)))

    return {
        "form": "multiplicative" if rmse_mult <= rmse_add else "additive",
        "multiplicative_ratio": round(a, 4),
        "additive_per_90": round(b, 4),
        "rmse_multiplicative": round(rmse_mult, 4),
        "rmse_additive": round(rmse_add, 4),
        "n": int(len(usable)),
    }


def _ratio(group: pd.DataFrame) -> float:
    api_rate = group["api_fouls"].sum() / (group["api_minutes"].sum() / 90.0)
    arch_rate = group["arch_fouls"].sum() / (group["arch_minutes"].sum() / 90.0)
    return float(api_rate / arch_rate)


def ratio_by_volume(matched: pd.DataFrame, bins: int = 5) -> pd.DataFrame:
    """The ratio per archive-rate quantile.

    Flat across volume supports a multiplicative correction. Falling with
    volume would mean the gap is additive and a scalar would inflate the
    tails, which is the distortion advisor 1 warned about.
    """
    usable = matched[matched["comparable"]].copy()
    usable["arch_rate"] = usable["arch_fouls"] / (usable["arch_minutes"] / 90.0)
    usable["bin"] = pd.qcut(usable["arch_rate"], q=bins, duplicates="drop")
    rows = [
        {"bin": str(interval), "n": len(group), "ratio": round(_ratio(group), 4)}
        for interval, group in usable.groupby("bin", observed=True)
    ]
    return pd.DataFrame(rows)


def ratio_by_position(matched: pd.DataFrame) -> pd.DataFrame:
    usable = matched[matched["comparable"] & (matched["position"] != "")].copy()
    usable["role"] = usable["position"].astype(str).str.split(",").str[0].str.strip()
    rows = [
        {"position": role, "n": len(group), "ratio": round(_ratio(group), 4)}
        for role, group in usable.groupby("role")
        if len(group) >= 30
    ]
    return pd.DataFrame(rows)


def write_reference(matched: pd.DataFrame, report: dict, path: Path = REFERENCE) -> dict:
    """The measured correction, with provenance, for the C1 blend to read."""
    fit = form_fit(matched)
    table = league_table(matched)
    held = {
        "measuredAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "global": {"ratio": round(_ratio(matched[matched["comparable"]]), 4)},
        "form": fit["form"],
        "multiplicative_ratio": fit["multiplicative_ratio"],
        "additive_per_90": fit["additive_per_90"],
        "seasons": {
            season_label(int(row["season"])): row["ratio"] for _, row in table.iterrows()
        },
        "pairs": report["pairs"],
        "unmatched_api": report["unmatched_api"],
        "minutes_disagree": report["minutes_disagree"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=2) + "\n")
    return held


def _complete_archive_seasons(archive: pd.DataFrame) -> pd.DataFrame:
    """Drop seasons the archive holds only part of.

    The file froze on 14 September 2025, so 2025/26 carries four matchweeks
    and would read as a wild per-player disagreement rather than a provider
    difference. A season is complete when its last match falls in late spring,
    or in July for 2019/20, which COVID stretched to the 26th of that month.
    """
    last = archive.groupby("season")["kickoff_utc"].max()
    complete = last[last.dt.month.isin((4, 5, 6, 7))].index
    return archive[archive["season"].isin(complete)]


def main() -> None:
    from foulgorithm.store import player_seasons
    from foulgorithm.store.players import load_player_matches

    api = player_seasons.load()
    api = api[api["season"].astype(str).str.match(r"\d{4}/\d{2}")]
    archive = _complete_archive_seasons(load_player_matches())

    matched, report = pair(api, archive)
    print(f"pairs: {report['pairs']}  unmatched: {report['unmatched_api']}  "
          f"ambiguous: {report['ambiguous_api']}  minutes disagree: {report['minutes_disagree']}\n")
    print(league_table(matched).to_string(index=False), "\n")
    print(form_fit(matched), "\n")
    print("by volume quintile:")
    print(ratio_by_volume(matched).to_string(index=False), "\n")
    print("by position:")
    print(ratio_by_position(matched).to_string(index=False), "\n")

    held = write_reference(matched, report)
    print(f"written to {REFERENCE} (global ratio {held['global']['ratio']}, form {held['form']})")


if __name__ == "__main__":
    main()
