"""football-data.co.uk adapter.

Match-level history for the backtest spine. Free CSVs, no account, no scraping.
Fouls and referees run from 2000/01, full closing odds from 2019/20.

Verified 21 August 2026. Three traps this module exists to handle:

  1. A season file that does not exist yet returns HTTP 300 with an HTML body,
     not a 404. Checking `response.ok` alone would ingest HTML as CSV.
  2. HxG and AxG columns appeared in 2026/27, inserted between Referee and HS.
     Everything is parsed by column NAME. Never by position.
  3. English cards exclude the first yellow when a second converts to a red, so
     `home_yellows` is not the count of yellow cards shown.
"""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from foulgorithm.sources.base import RawResponse, SourceError, utcnow

BASE_URL = "https://www.football-data.co.uk/mmz4281"
SOURCE = "football_data"

# Absent any of these, we raise rather than guess. Odds columns are deliberately
# not required: they only exist from 2019/20 and their absence is expected.
REQUIRED_COLUMNS = (
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "Referee",
    "HF",
    "AF",
    "HY",
    "AY",
    "HR",
    "AR",
)

_COLUMN_MAP = {
    "home_goals": "FTHG",
    "away_goals": "FTAG",
    "home_fouls": "HF",
    "away_fouls": "AF",
    "home_yellows": "HY",
    "away_yellows": "AY",
    "home_reds": "HR",
    "away_reds": "AR",
    "home_shots": "HS",
    "away_shots": "AS",
    "home_shots_on_target": "HST",
    "away_shots_on_target": "AST",
    "home_corners": "HC",
    "away_corners": "AC",
}

_SEASON_LABEL = re.compile(r"^(\d{4})-(\d{2})$")

# Full-time statistics publish shortly after the whistle. Three hours past
# kickoff is comfortably conservative.
_STATS_DELAY = timedelta(hours=3)

# Rows without a kickoff time are treated as a late kickoff, so known_at errs
# later rather than earlier. Erring earlier would leak.
_ASSUMED_LATE_KICKOFF = 20


def season_code(label: str) -> str:
    """Convert a season label like '2025-26' to the site's '2526'."""
    match = _SEASON_LABEL.match(label)
    if not match:
        raise ValueError(f"season label must look like '2025-26', got {label!r}")
    start, end = match.groups()
    return f"{int(start) % 100:02d}{end}"


def url_for(season: str, division: str = "E0") -> str:
    """Division is a parameter, not a constant. Nothing here is Premier League only."""
    return f"{BASE_URL}/{season_code(season)}/{division}.csv"


def fetch(season: str, division: str = "E0", cache_root: Path | None = None) -> RawResponse:
    """Fetch a season file, serving from the local cache when present.

    A settled season never changes, so it is fetched once and read from disk
    forever after. That keeps development offline and keeps us off the site.
    """
    url = url_for(season, division)
    cache_root = cache_root or Path("data/raw")
    cached = cache_root / SOURCE / f"{season_code(season)}_{division}.csv"

    if cached.exists():
        return RawResponse(
            source=SOURCE,
            url=url,
            content=cached.read_bytes(),
            content_type="text/csv",
            status_code=200,
            fetched_at=datetime.fromtimestamp(cached.stat().st_mtime, tz=timezone.utc),
        )

    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = RawResponse(
                source=SOURCE,
                url=url,
                content=response.read(),
                content_type=response.headers.get("Content-Type", ""),
                status_code=response.status,
                fetched_at=utcnow(),
            )
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{url} returned HTTP {exc.code}") from exc

    validate(raw)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(raw.content)
    time.sleep(1)  # be polite, this is a free service run by one person
    return raw


def _user_agent() -> str:
    import os

    contact = os.environ.get("SCRAPER_CONTACT_EMAIL", "").strip()
    return f"foulgorithm/0.1 (+{contact})" if contact else "foulgorithm/0.1"


def validate(raw: RawResponse) -> None:
    if raw.status_code != 200:
        raise SourceError(
            f"{raw.url} returned HTTP {raw.status_code}. A season file that does not "
            "exist yet returns 300 with an HTML body, so this is likely a season we "
            "cannot load rather than an outage."
        )
    if "csv" not in raw.content_type and "text/plain" not in raw.content_type:
        raise SourceError(f"{raw.url} returned content type {raw.content_type!r}, expected CSV")
    if not raw.content.strip():
        raise SourceError(f"{raw.url} returned an empty body")


def parse(raw: RawResponse) -> list[dict]:
    validate(raw)

    reader = csv.DictReader(io.StringIO(raw.text()))
    if reader.fieldnames is None:
        raise SourceError(f"{raw.url} has no header row")

    present = {name.strip() for name in reader.fieldnames if name}
    missing = [c for c in REQUIRED_COLUMNS if c not in present]
    if missing:
        raise SourceError(f"{raw.url} is missing required columns: {', '.join(missing)}")

    rows: list[dict] = []
    for line_no, record in enumerate(reader, start=2):
        record = {(k.strip() if k else k): v for k, v in record.items()}
        if not (record.get("Date") or "").strip():
            continue  # trailing blank rows are normal in these files

        kickoff = _kickoff(record, raw.url, line_no)
        row = {
            "source": SOURCE,
            "source_url": raw.url,
            "kickoff_utc": kickoff,
            "known_at": kickoff + _STATS_DELAY,
            "home_team_raw": _required_text(record, "HomeTeam", raw.url, line_no),
            "away_team_raw": _required_text(record, "AwayTeam", raw.url, line_no),
            "referee_raw": (record.get("Referee") or "").strip() or None,
        }
        for field, column in _COLUMN_MAP.items():
            row[field] = _optional_int(record.get(column))
        for field in ("home_fouls", "away_fouls", "home_goals", "away_goals"):
            if row[field] is None:
                raise SourceError(f"{raw.url} line {line_no}: {field} is blank")
        rows.append(row)

    if not rows:
        raise SourceError(f"{raw.url} parsed to zero rows")
    return rows


def _kickoff(record: dict, url: str, line_no: int) -> datetime:
    date_text = (record.get("Date") or "").strip()
    day = None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            day = datetime.strptime(date_text, fmt)
            break
        except ValueError:
            continue
    if day is None:
        raise SourceError(f"{url} line {line_no}: cannot parse date {date_text!r}")

    time_text = (record.get("Time") or "").strip()
    if time_text:
        try:
            clock = datetime.strptime(time_text, "%H:%M")
        except ValueError as exc:
            raise SourceError(f"{url} line {line_no}: cannot parse time {time_text!r}") from exc
        hour, minute = clock.hour, clock.minute
    else:
        hour, minute = _ASSUMED_LATE_KICKOFF, 0

    return day.replace(hour=hour, minute=minute, tzinfo=timezone.utc)


def _required_text(record: dict, column: str, url: str, line_no: int) -> str:
    value = (record.get(column) or "").strip()
    if not value:
        raise SourceError(f"{url} line {line_no}: {column} is blank")
    return value


def _optional_int(value: str | None) -> int | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None
