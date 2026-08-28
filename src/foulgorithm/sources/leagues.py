"""Player-match files for the big five leagues, from the archive we already use.

We read one of twenty-four `misc` files in a release we already depend on. The
other five carry an identical schema and roughly 370,000 additional
player-matches, for the cost of five downloads.

**Every row carries its league, and that is not decoration.** Serie A runs 1.197
fouls per 90 against England's 0.972, a 23% gap, while England's own eight-season
spread is about 9%. The league effect is more than twice the season effect, so
concatenating these files without a league column would overstate every Italian
player by roughly a fifth. Pooled with a fitted league offset it is sound; that
is roadmap item 8, and it is deliberately not done here.

All six froze on 17 September 2025 when the archive was abandoned. This adds
volume, never recency.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from foulgorithm.sources.base import SourceError

RELEASE = "https://github.com/JaseZiv/worldfootballR_data/releases/download/fb_advanced_match_stats"

CACHE = Path("data/raw/worldfootballr")


@dataclass(frozen=True)
class League:
    code: str
    name: str
    file_stem: str
    tier: int


LEAGUES: dict[str, League] = {
    "ENG": League("ENG", "Premier League", "ENG_M_1st", 1),
    "ESP": League("ESP", "La Liga", "ESP_M_1st", 1),
    "ITA": League("ITA", "Serie A", "ITA_M_1st", 1),
    "GER": League("GER", "Bundesliga", "GER_M_1st", 1),
    "FRA": League("FRA", "Ligue 1", "FRA_M_1st", 1),
    "USA": League("USA", "Major League Soccer", "USA_M_1st", 1),
}

#: FBref's names on the left, ours on the right. Anything not listed is dropped.
COLUMNS = {
    "Player": "player",
    "Team": "team",
    "Min": "minutes",
    "Pos": "position",
    "Fls": "fouls_committed",
    "Fld": "fouls_drawn",
    "CrdY": "yellows",
    "CrdR": "reds",
    "TklW": "tackles_won",
    "Int": "interceptions",
    "Match_Date": "match_date",
    "Season_End_Year": "season",
}


def url_for(code: str) -> str:
    league = LEAGUES[code]
    return f"{RELEASE}/{league.file_stem}_misc_player_advanced_match_stats.csv"


def path_for(code: str, root: Path = CACHE) -> Path:
    return root / f"{code.lower()}_misc_player_match.csv"


def normalise(row: dict, code: str) -> dict:
    """One FBref row in our shape, with its league on it.

    Opponent and venue are derived from the two club names rather than trusted
    from a column, because the file has `Home_Team` and `Away_Team` but no
    "opponent": the row knows which club the PLAYER is on and the fixture knows
    the other two.
    """
    out = {ours: row.get(theirs) for theirs, ours in COLUMNS.items()}

    team = (row.get("Team") or "").strip()
    home = (row.get("Home_Team") or "").strip()
    away = (row.get("Away_Team") or "").strip()

    at_home = team == home
    out["opponent"] = away if at_home else home
    out["venue"] = "home" if at_home else "away"

    # The 23% gap between leagues means a row that has lost its league is a row
    # that will quietly mislead whoever pools it.
    out["league"] = code
    out["source"] = "worldfootballr"
    return out


def download(code: str, root: Path = CACHE, force: bool = False) -> Path:
    """Fetch one league's file, once, and record where it came from."""
    if code not in LEAGUES:
        raise KeyError(f"unknown league {code!r}. Known: {sorted(LEAGUES)}")

    path = path_for(code, root)
    if path.exists() and not force:
        # A file already on disk still needs its provenance recorded. Returning
        # early skipped it, so England, the one file that predated this module,
        # was the only league with no record of where it came from. That is
        # precisely the league whose staleness went unnoticed for eleven months.
        _record_provenance(code, url_for(code), path, path.stat().st_size, root)
        return path

    root.mkdir(parents=True, exist_ok=True)
    url = url_for(code)
    request = urllib.request.Request(url, headers={"User-Agent": "foulgorithm/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            if response.status != 200:
                raise SourceError(f"{url} returned HTTP {response.status}")
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{url} returned HTTP {exc.code}") from exc

    path.write_bytes(body)
    _record_provenance(code, url, path, len(body), root)
    return path


def _record_provenance(code: str, url: str, path: Path, size: int, root: Path) -> None:
    """Where this file came from and when.

    The absence of exactly this is how the previous source sat frozen for eleven
    months without anyone noticing it had stopped moving.
    """
    manifest = root / "manifest.json"
    held = {}
    if manifest.exists():
        try:
            held = json.loads(manifest.read_text())
        except json.JSONDecodeError:
            held = {}

    held[code] = {
        "league": LEAGUES[code].name,
        "url": url,
        "file": path.name,
        "bytes": size,
        "fetchedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    manifest.write_text(json.dumps(held, indent=1, sort_keys=True))


def main() -> None:
    """`make leagues`. Downloads every big-five file we do not already hold."""
    for code in LEAGUES:
        path = path_for(code)
        if path.exists():
            print(f"  {code}  already held, {path.stat().st_size / 1e6:.0f} MB")
            continue
        print(f"  {code}  fetching...", flush=True)
        got = download(code)
        print(f"  {code}  {got.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
