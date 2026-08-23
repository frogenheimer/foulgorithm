"""What each fixture card actually said, kept so it can be marked right or wrong.

The three options on a card are regenerated on every publish, so nothing
recorded what a reader saw at any moment. Once the game is played there is no
way to show whether the call came in, which is the cheapest useful feedback the
site can offer and the whole reason for publishing before kickoff.

**Versioned, not write-once.** A midweek model change SHOULD produce different
picks, and freezing the first version would misrepresent what we were saying by
Saturday. Every version is kept.

**The last version published before kickoff is the one that counts**, because
that is what was on the card when the game started. A version written after the
whistle is kept for the record and never scored, so a rerun cannot quietly
rewrite what we called.

This is the same discipline as the claim ledger and the slate store, applied to
the thing a reader actually looks at.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

STORE = Path("data/picks")


def _slug(fixture: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in fixture.lower()).strip("-")


def _path(fixture: str, root: Path = STORE) -> Path:
    return root / f"{_slug(fixture)}.json"


def versions(fixture: str, root: Path = STORE) -> list[dict]:
    path = _path(fixture, root)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text()).get("versions", [])
    except json.JSONDecodeError:
        return []


def _same(a: list[dict], b: list[dict]) -> bool:
    """Whether two sets of options say the same thing.

    Compared on what a reader sees, not on the whole object: the price, the
    total and the legs. Re-running the pipeline with unchanged inputs rounds
    identically, so anything that differs here is a real change of mind.
    """

    def shape(options):
        return [
            (
                o.get("band"),
                o.get("character"),
                round(float(o.get("odds") or 0), 2),
                o.get("totalFouls"),
                tuple(sorted((l["player"], l["fouls"], l["market"]) for l in o.get("legs", []))),
            )
            for o in options
        ]

    return shape(a) == shape(b)


def record(
    fixture: str,
    kickoff: str,
    options: list[dict],
    published_at: str,
    root: Path = STORE,
) -> int:
    """Keep this version if it differs from the last. Returns the version number.

    Zero when there was nothing to record or nothing had changed.
    """
    if not options:
        return 0

    held = versions(fixture, root)
    if held and _same(held[-1]["options"], options):
        return 0

    entry = {
        "version": len(held) + 1,
        "publishedAt": published_at,
        "options": options,
    }
    held.append(entry)

    path = _path(fixture, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fixture": fixture, "kickoff": kickoff, "versions": held}, indent=1)
    )
    return entry["version"]


def final(fixture: str, root: Path = STORE) -> dict | None:
    """The last version published before kickoff, which is the one that counts."""
    path = _path(fixture, root)
    if not path.exists():
        return None
    try:
        held = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None

    kickoff = datetime.fromisoformat(held["kickoff"].replace("Z", "+00:00"))
    before = [
        v
        for v in held.get("versions", [])
        if datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00")) < kickoff
    ]
    return before[-1] if before else None


def score(option: dict, outcomes: dict[tuple, bool]) -> dict:
    """Mark one option's legs against what happened.

    `outcomes` maps (player, market, line) to whether the line was cleared.

    Three states per leg and three for the card, because two is a lie: an
    unsettled leg shown as missed reads as a loss we have not had. A card lands
    only when every leg does, and it is lost the moment ONE leg misses, since
    waiting on the rest cannot bring a combination back.
    """
    legs = []
    for leg in option.get("legs", []):
        key = (leg["player"], leg["market"], float(leg["fouls"]) - 0.5)
        legs.append({**leg, "landed": outcomes.get(key)})

    if any(l["landed"] is False for l in legs):
        landed = False
    elif legs and all(l["landed"] is True for l in legs):
        landed = True
    else:
        landed = None

    return {**option, "legs": legs, "landed": landed}


def load_all(root: Path = STORE) -> dict[str, dict]:
    """Every fixture we have ever published a card for."""
    if not root.exists():
        return {}
    out = {}
    for path in sorted(root.glob("*.json")):
        try:
            held = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        out[held["fixture"]] = held
    return out
