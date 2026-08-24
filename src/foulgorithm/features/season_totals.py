"""Official season totals as dated evidence for the player rate.

The player's own rate is the largest input to every prediction, and its
per-match source froze in September 2025. The league's own season totals are
current and reach back to 2006/07. This module turns them into pseudo-evidence
the empirical-Bayes rate can digest, under the C1 rules of
`docs/34-final-plan.md`:

- **Dated, never a block.** A season total is spread across the part of the
  season the archive does not cover, as month-slice rows the decay machinery
  treats like any other dated evidence. An undated aggregate would flatten
  recency, which was advisor 1's sharpest objection.
- **Event time and knowability are different columns.** Decay runs on
  `event_at`, the middle of the month slice. Leakage filtering runs on
  `known_at`: a completed season was knowable at its end, an in-progress
  total only at the moment we read it.
- **Exactly nothing where the archive is complete.** The residual against
  archive coverage decides what enters. Complete coverage means no rows,
  which is the double-count release gate, testable as an equality.
- **Anomalies are surfaced, not clipped into shape.** API fouls materially
  below what the archive already saw means identity or scope is wrong
  somewhere, and that player-season is excluded and counted.
- **Zero is evidence.** The fouls table omits zero-foul players. After the
  pagination repair, minutes-present-fouls-absent was verified to mean zero
  fouls for 67 of 69 determinable players, so it enters as exculpatory
  pseudo-evidence, flagged `zero-inferred`.

The provider offset is read from `data/reference/provider_offset.json`,
measured at 1.000 on 2026-08-24. The machinery stays because the measurement
could change; the constant is never typed here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from foulgorithm.identity.players import resolve_names

OFFSET_REFERENCE = Path("data/reference/provider_offset.json")

#: Residual fouls this far below zero are identity or scope, not noise.
ANOMALY_TOLERANCE = 2.0

#: A residual below this many minutes is coverage jitter, not a missing
#: stretch of season, and produces no rows.
MIN_RESIDUAL_MINUTES = 90.0

COLUMNS = [
    "player",
    "season",
    "event_at",
    "known_at",
    "minutes",
    "fouls_committed",
    "fouls_drawn",
    "kind",
    "source",
]

_last_report: dict = {}


def last_report() -> dict:
    """What the most recent `evidence` call kept out, for the integrity gates."""
    return dict(_last_report)


def season_window(label: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """August to May, except the COVID season, which ran to late July."""
    start_year = int(str(label)[:4])
    start = pd.Timestamp(f"{start_year}-08-01", tz="UTC")
    end_day = f"{start_year + 1}-07-31" if str(label) == "2019/20" else f"{start_year + 1}-05-31"
    return start, pd.Timestamp(end_day, tz="UTC")


def load_offset(path: Path = OFFSET_REFERENCE) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"seasons": {}, "global": {"ratio": 1.0}}


def _month_slices(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[pd.Timestamp, float]]:
    """(midpoint, share) per calendar month overlapping the window.

    Shares are proportional to days, so a window cut short by the archive or
    by the fetch date weights its months accordingly rather than equally.
    """
    if end <= start:
        return []
    months = pd.period_range(start, end, freq="M")
    slices = []
    for month in months:
        seg_start = max(start, month.start_time.tz_localize("UTC"))
        seg_end = min(end, month.end_time.tz_localize("UTC"))
        days = (seg_end - seg_start).total_seconds()
        if days <= 0:
            continue
        slices.append((seg_start + (seg_end - seg_start) / 2, days))
    total = sum(days for _, days in slices)
    return [(mid, days / total) for mid, days in slices]


def evidence(
    api: pd.DataFrame,
    archive: pd.DataFrame,
    offset: dict | None = None,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Pseudo-evidence rows from season totals, in archive name space.

    API names resolve to archive names through the identity rules. A name
    that does not resolve keeps its own: those are overwhelmingly players
    with no archive record at all, which is exactly who this evidence is
    for. The residual risk, a player present in the archive under a variant
    spelling being double-counted, is carried in the report as `unresolved`
    and settled over time in the crosswalk.
    """
    global _last_report
    offset = offset if offset is not None else load_offset()
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")

    usable = api[pd.to_numeric(api["mins_played"], errors="coerce").notna()].copy()

    resolution = resolve_names(sorted(usable["player"].unique()), archive["player"].unique())
    usable["resolved"] = usable["player"].map(resolution.matched).fillna(usable["player"])

    arch = archive.groupby(["player", "season"]).agg(
        arch_minutes=("minutes", "sum"),
        arch_fc=("fouls_committed", "sum"),
        arch_fd=("fouls_drawn", "sum"),
        arch_last=("kickoff_utc", "max"),
    )

    rows: list[dict] = []
    anomalies = 0

    for record in usable.itertuples(index=False):
        label = str(record.season)
        start, end = season_window(label)
        ratio = (offset.get("seasons") or {}).get(label) or (offset.get("global") or {}).get(
            "ratio", 1.0
        )

        minutes = float(record.mins_played)
        fouls = pd.to_numeric(pd.Series([record.fouls]), errors="coerce").iloc[0]
        drawn = pd.to_numeric(pd.Series([record.was_fouled]), errors="coerce").iloc[0]
        zero_inferred = pd.isna(fouls)
        fc = 0.0 if zero_inferred else float(fouls) / ratio
        fd = 0.0 if pd.isna(drawn) else float(drawn) / ratio

        end_year = int(label[:4]) + 1
        covered = arch.loc[(record.resolved, end_year)] if (record.resolved, end_year) in arch.index else None

        if covered is not None:
            residual_minutes = minutes - float(covered["arch_minutes"])
            residual_fc = fc - float(covered["arch_fc"])
            residual_fd = fd - float(covered["arch_fd"])
            if residual_fc < -ANOMALY_TOLERANCE or residual_fd < -ANOMALY_TOLERANCE:
                anomalies += 1
                continue
            if residual_minutes < MIN_RESIDUAL_MINUTES:
                continue
            minutes, fc, fd = residual_minutes, max(residual_fc, 0.0), max(residual_fd, 0.0)
            start = max(start, pd.Timestamp(covered["arch_last"]) + pd.Timedelta(days=1))
            kind = "residual"
        else:
            kind = "zero-inferred" if zero_inferred else "whole-season"

        fetched = pd.Timestamp(record.fetchedAt) if getattr(record, "fetchedAt", None) else now
        if fetched.tzinfo is None:
            fetched = fetched.tz_localize("UTC")
        in_progress = fetched < end
        known_at = fetched if in_progress else end
        window_end = min(end, fetched) if in_progress else end

        for event_at, share in _month_slices(start, window_end):
            rows.append(
                {
                    "player": record.resolved,
                    "season": label,
                    "event_at": event_at,
                    "known_at": known_at,
                    "minutes": minutes * share,
                    "fouls_committed": fc * share,
                    "fouls_drawn": fd * share,
                    "kind": kind,
                    "source": "league-season-totals",
                }
            )

    _last_report = {
        "rows": len(rows),
        "players": len({r["player"] for r in rows}),
        "anomalies": anomalies,
        "unresolved": len(resolution.unmatched),
    }
    return pd.DataFrame(rows, columns=COLUMNS)
