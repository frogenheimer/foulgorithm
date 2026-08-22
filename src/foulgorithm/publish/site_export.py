"""Build the JSON the site reads.

The site has no backend. Python computes everything and writes a static file,
which Next.js reads at build time. That keeps hosting free and the page fast.

When the database lands this module changes its input, not its output, so the
site's data contract stays put.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from foulgorithm.sources import football_data

DEFAULT_OUTPUT = Path("site/public/data/overview.json")

# Fouls and referees start in 2000/01. Earlier files carry results only.
FIRST_SEASON = 2000


def season_labels(first: int = FIRST_SEASON, last: int | None = None) -> list[str]:
    """Generate season labels. Never hard-coded: the roster follows the calendar."""
    if last is None:
        last = _latest_settled_season()
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(first, last + 1)]


def _latest_settled_season() -> int:
    """The most recent season whose file exists. A season in progress is fine."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    # A season starting in August of year Y is labelled Y-(Y+1).
    return now.year - 1 if now.month < 8 else now.year


def load_matches(seasons: list[str]) -> list[dict]:
    matches: list[dict] = []
    for label in seasons:
        try:
            rows = football_data.parse(football_data.fetch(label))
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            print(f"  skipped {label}: {exc}")
            continue
        for row in rows:
            row["season"] = label
        matches.extend(rows)
        print(f"  {label}: {len(rows)} matches")
    return matches


def build(matches: list[dict]) -> dict:
    by_season: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_season[m["season"]].append(m)

    season_series = []
    for label in sorted(by_season):
        rows = by_season[label]
        fouls = [r["home_fouls"] + r["away_fouls"] for r in rows]
        cards = [
            (r["home_yellows"] or 0)
            + (r["away_yellows"] or 0)
            + (r["home_reds"] or 0)
            + (r["away_reds"] or 0)
            for r in rows
        ]
        season_series.append(
            {
                "season": label,
                "matches": len(rows),
                "foulsPerMatch": round(statistics.mean(fouls), 2),
                "cardsPerMatch": round(statistics.mean(cards), 2),
                "stdev": round(statistics.pstdev(fouls), 2),
            }
        )

    latest = max(by_season)
    recent = [m for m in matches if m["season"] >= _shift(latest, -2)]

    return {
        "generatedAt": _now_iso(),
        "coverage": {
            "seasons": len(by_season),
            "matches": len(matches),
            "firstSeason": min(by_season),
            "lastSeason": latest,
        },
        "headline": _headline(season_series, matches),
        "seasons": season_series,
        "distribution": _distribution(matches),
        "referees": _referees(recent),
        "appointments": _appointments(),
        "teams": _teams(recent),
        "homeAway": _home_away(recent),
        "recentWindow": f"{_shift(latest, -2)} to {latest}",
    }


def _headline(season_series: list[dict], matches: list[dict]) -> dict:
    first, last = season_series[0], season_series[-1]
    change = (last["foulsPerMatch"] - first["foulsPerMatch"]) / first["foulsPerMatch"]
    fouls = [m["home_fouls"] + m["away_fouls"] for m in matches]
    return {
        "foulsPerMatchNow": last["foulsPerMatch"],
        "foulsPerMatchThen": first["foulsPerMatch"],
        "changePct": round(change * 100, 1),
        "meanAllTime": round(statistics.mean(fouls), 2),
        "spanYears": len(season_series),
    }


def _distribution(matches: list[dict]) -> list[dict]:
    counts: dict[int, int] = defaultdict(int)
    for m in matches:
        counts[m["home_fouls"] + m["away_fouls"]] += 1
    total = len(matches)
    return [
        {"fouls": k, "matches": counts[k], "share": round(counts[k] / total, 5)}
        for k in sorted(counts)
        if 4 <= k <= 50
    ]


def _appointments() -> list[dict]:
    """Who has which fixture this round.

    Without it the referee table is trivia. With it, a reader can see that the
    man 12% above the league on fouls has the game they were looking at.
    """
    try:
        from foulgorithm.sources import football_data as fd

        return [
            {
                "referee": row["referee_raw"],
                "fixture": f"{row['home_team_raw']} v {row['away_team_raw']}",
                "kickoff": row["kickoff_utc"].isoformat(),
            }
            for row in fd.fetch_fixtures()
            if row.get("referee_raw")
        ]
    except Exception:
        # A missing appointment list makes the page thinner, not wrong.
        return []


def _referees(matches: list[dict], minimum: int = 20) -> list[dict]:
    """Per-referee observations. Not a referee effect, and the site says so.

    `cardsPerFoul` is the column worth reading. Cards per match rises with how
    physical a game was, so it partly measures the fixtures a referee drew.
    Cards per foul asks how likely he is to book an offence he has already
    given, which is much closer to what people mean by strict.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        if m["referee_raw"]:
            grouped[m["referee_raw"]].append(m)

    league_mean = statistics.mean(m["home_fouls"] + m["away_fouls"] for m in matches)
    out = []
    for name, rows in grouped.items():
        if len(rows) < minimum:
            continue
        fouls = [r["home_fouls"] + r["away_fouls"] for r in rows]
        mean = statistics.mean(fouls)

        # Older season files carry results without cards. Counting a missing
        # card column as zero would read as "never books anyone", so those
        # matches are excluded from the card figures rather than folded in.
        carded = [
            r for r in rows
            if r.get("home_yellows") is not None and r.get("away_yellows") is not None
        ]
        cards = [(r["home_yellows"] or 0) + (r["away_yellows"] or 0) for r in carded]
        reds = [(r.get("home_reds") or 0) + (r.get("away_reds") or 0) for r in carded]
        card_fouls = [r["home_fouls"] + r["away_fouls"] for r in carded]
        total_fouls = sum(card_fouls)

        out.append(
            {
                "referee": name,
                "matches": len(rows),
                "foulsPerMatch": round(mean, 2),
                "cardsPerMatch": round(statistics.mean(cards), 2) if cards else None,
                "redsPerMatch": round(statistics.mean(reds), 2) if reds else None,
                "cardsPerFoul": round(sum(cards) / total_fouls, 4) if total_fouls else None,
                "cardedMatches": len(carded),
                # Raw ratio only. It is confounded by which teams a referee was
                # assigned, and the model must not use it. Shown here as an
                # observation, not as a multiplier. See docs/06-modelling.md.
                "vsLeague": round(mean / league_mean, 3),
            }
        )
    return sorted(out, key=lambda r: -r["foulsPerMatch"])


def _teams(matches: list[dict], minimum: int = 20) -> list[dict]:
    committed: dict[str, list[int]] = defaultdict(list)
    drawn: dict[str, list[int]] = defaultdict(list)
    for m in matches:
        committed[m["home_team_raw"]].append(m["home_fouls"])
        committed[m["away_team_raw"]].append(m["away_fouls"])
        drawn[m["home_team_raw"]].append(m["away_fouls"])
        drawn[m["away_team_raw"]].append(m["home_fouls"])

    out = []
    for team, values in committed.items():
        if len(values) < minimum:
            continue
        out.append(
            {
                "team": team,
                "matches": len(values),
                "committedPerMatch": round(statistics.mean(values), 2),
                "drawnPerMatch": round(statistics.mean(drawn[team]), 2),
            }
        )
    return sorted(out, key=lambda r: -r["committedPerMatch"])


def _home_away(matches: list[dict]) -> dict:
    home = [m["home_fouls"] for m in matches]
    away = [m["away_fouls"] for m in matches]
    home_cards = [(m["home_yellows"] or 0) for m in matches]
    away_cards = [(m["away_yellows"] or 0) for m in matches]
    return {
        "homeFouls": round(statistics.mean(home), 2),
        "awayFouls": round(statistics.mean(away), 2),
        "homeYellows": round(statistics.mean(home_cards), 2),
        "awayYellows": round(statistics.mean(away_cards), 2),
    }


def _shift(label: str, years: int) -> str:
    start = int(label[:4]) + years
    return f"{start}-{(start + 1) % 100:02d}"


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def export(output: Path = DEFAULT_OUTPUT) -> Path:
    print("Loading seasons...")
    matches = load_matches(season_labels())
    if not matches:
        raise SystemExit("no matches loaded")
    payload = build(matches)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    c = payload["coverage"]
    print(f"\nWrote {output}")
    print(f"  {c['matches']} matches across {c['seasons']} seasons "
          f"({c['firstSeason']} to {c['lastSeason']})")
    return output


if __name__ == "__main__":
    export()
