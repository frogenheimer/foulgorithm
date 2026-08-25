"""Played fixtures keep their pages.

The payload only ever holds the round being predicted, so a game's page
vanished at the first publish after its kickoff, taking with it the picks a
reader might want to check against what happened. Every publish now writes
each fixture's page data to its own file under site/public/data/fixtures/,
and settle marks the ladder legs with outcomes once they exist. The site
builds a page from every file here, so the record outlives the round.

Two rules keep it honest. A later publish replaces an earlier one only
BEFORE kickoff, mirroring the binding rule for slates: what the page shows
for a played game is what was published before it started, never a
retrofit. And marking outcomes only ever ADDS the outcomes and result
blocks; the published ladder itself is never rewritten.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("site/public/data/fixtures")


def fixture_slug(label: str) -> str:
    """"Arsenal v Coventry" -> "arsenal-v-coventry". Must match site/lib/slug.ts."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def _short_market(market: str) -> str:
    return "drawn" if market.endswith("drawn") else "committed"


def slice_payload(payload: dict, label: str) -> dict | None:
    """One fixture's page data out of a full payload. None if it is not there."""
    ladder = (payload.get("fixtureSlips") or {}).get(label)
    if not ladder:
        return None

    board = next(
        (
            f
            for f in payload.get("board") or []
            if f"{f.get('home')} v {f.get('away')}" == label
        ),
        {},
    )
    explorer = payload.get("explorer") or {}
    return {
        "label": label,
        "slug": fixture_slug(label),
        "publishedAt": payload.get("generatedAt", ""),
        "kickoff": board.get("kickoff", ""),
        "referee": board.get("referee"),
        "competition": board.get("competition"),
        "houseSheet": board.get("houseSheet"),
        "characters": [
            {"id": p.get("id"), "name": p.get("name"), "generation": p.get("generation")}
            for p in payload.get("picks") or []
        ],
        "ladder": ladder,
        # The five's three bets each on this game (docs/38), when the payload
        # carries the per-game shape. Round-wide payloads from before leave
        # this empty and the page copes.
        "bets": ((payload.get("slates") or {}).get("byGame") or {}).get(label),
        "formations": (payload.get("formations") or {}).get(label),
        "explorer": {
            "models": explorer.get("models", []),
            "lines": explorer.get("lines", []),
            "markets": explorer.get("markets", []),
            "house": explorer.get("house", ""),
            "rows": [r for r in explorer.get("rows") or [] if r.get("fixture") == label],
        },
    }


def matchday_slice(matchday: dict | None, label: str) -> dict | None:
    """One fixture's head-to-head sheet out of the matchday export."""
    if not matchday:
        return None
    fixture = next(
        (
            f
            for f in matchday.get("fixtures") or []
            if f"{f.get('home')} v {f.get('away')}" == label
        ),
        None,
    )
    if fixture is None:
        return None
    return {
        "window": matchday.get("window"),
        "seasons": matchday.get("seasons"),
        "note": matchday.get("note"),
        "fixture": fixture,
    }


def write_round(payload: dict, root: Path = ROOT, matchday: dict | None = None) -> int:
    """Archive every fixture in a payload. Returns how many files changed.

    A publish only ever lands in the archive when it happened BEFORE the
    fixture's kickoff, mirroring the binding rule for slates: the archived
    page shows what was on the board when the game started, never a
    retrofit. Outcome blocks already attached by settle are carried over,
    and a head-to-head sheet, once captured, survives the sheet's own file
    rolling on to the next round.
    """
    if matchday is None:
        matchday_path = Path("site/public/data/matchday.json")
        matchday = (
            json.loads(matchday_path.read_text()) if matchday_path.exists() else None
        )

    written = 0
    for label in payload.get("fixtureSlips") or {}:
        fresh = slice_payload(payload, label)
        if fresh is None:
            continue
        path = root / f"{fresh['slug']}.json"
        held = _read(path)
        kickoff = (held.get("kickoff") if held else "") or fresh["kickoff"]
        if kickoff and fresh["publishedAt"] > kickoff:
            continue  # published after kickoff: the archive stays as it was
        fresh["matchday"] = matchday_slice(matchday, label)
        if held:
            for keep in ("outcomes", "result", "gradedAt"):
                if held.get(keep) is not None:
                    fresh[keep] = held[keep]
            if fresh["matchday"] is None and held.get("matchday") is not None:
                fresh["matchday"] = held["matchday"]
        root.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fresh) + "\n")
        written += 1
    return written


def outcomes_for(label: str, graded: list[dict], predictions: list[dict]) -> dict:
    """Per-leg outcomes for one fixture: "fullName|market|line" -> won/observed.

    Joined through the claim ledger so a name never settles against another
    fixture's match: the graded row's key finds the prediction row, and the
    prediction row says which fixture it belonged to.
    """
    claims = {p["key"]: p for p in predictions if p.get("fixture") == label}
    out: dict[str, dict] = {}
    for row in graded:
        claim = claims.get(row.get("key"))
        if claim is None:
            continue
        key = f"{claim['entity']}|{_short_market(claim['market'])}|{claim['line']}"
        out[key] = {"won": bool(row.get("won")), "observed": row.get("observed")}
    return out


def mark_all(
    graded: list[dict] | None = None,
    predictions: list[dict] | None = None,
    season_fixtures: list[dict] | None = None,
    root: Path = ROOT,
) -> int:
    """Attach outcomes and results to every archived fixture that has them.

    Loads the stores itself when not handed data, so settle can call it with
    no arguments. Idempotent: a file marks again whenever new outcomes exist,
    because a fixture can settle in stages.
    """
    if graded is None:
        from foulgorithm.review import grade as grading

        graded = grading.load_all()
    if predictions is None:
        from foulgorithm.store import predictions as pred_store

        predictions = pred_store.load_all()
    if season_fixtures is None:
        season_path = Path("site/public/data/season.json")
        season_fixtures = (
            json.loads(season_path.read_text()).get("fixtures", [])
            if season_path.exists()
            else []
        )

    results = {
        f"{f.get('home')} v {f.get('away')}": f
        for f in season_fixtures
        if f.get("status") == "C"
    }

    marked = 0
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        held = _read(path)
        if not held:
            continue
        outcomes = outcomes_for(held["label"], graded, predictions)
        result = results.get(held["label"])
        if not outcomes and not result:
            continue
        changed = outcomes != (held.get("outcomes") or {})
        if result:
            block = {
                "score": result.get("score"),
                "result": result.get("result"),
                "matchweek": result.get("matchweek"),
            }
            if block != held.get("result"):
                held["result"] = block
                changed = True
        if not changed:
            continue
        if outcomes:
            held["outcomes"] = outcomes
        path.write_text(json.dumps(held) + "\n")
        marked += 1
    return marked


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
