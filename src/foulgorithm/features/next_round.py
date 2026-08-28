"""Which fixtures are next, and what we know about them.

Two sources, and which one is authoritative for what matters.

**The league's own fixture list decides what is played.** It knows the whole
season, so it always knows what is next.

**football-data.co.uk supplies the referee and the closing odds**, which the
league's list does not carry. It publishes one round at a time and does not roll
over until midweek, so on a Sunday evening nine of its ten fixtures have already
kicked off.

Reading the round from football-data, as the pipeline did, meant every pick was
generated for a game already played. The homepage renders a played fixture as a
result rather than a pick, so from Sunday night until the file rolled over the
site had no picks on it at all, which is the state it was found in.

So: the league's list chooses, football-data decorates, and a fixture with no
match in the decoration still gets predicted with the referee left unknown.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

#: How far past the first upcoming kickoff still counts as the same round.
#: A Premier League round runs Friday night to Monday night, so four days holds
#: one round and excludes the next.
ROUND_WINDOW = timedelta(days=4)

#: How far apart the two sources may put the same kickoff and still be joined.
#: They disagree on exact times far more often than on days.
KICKOFF_SLACK = timedelta(hours=6)


def _key(home: str, away: str) -> tuple[str, str]:
    return (str(home).strip().lower(), str(away).strip().lower())


def select(live_fixtures, enrichment: list[dict], now: datetime | None = None) -> list[dict]:
    """The next round, in the shape the pipeline already expects.

    `live_fixtures` are the league's, `enrichment` is football-data's. Returns
    an empty list rather than a played round when nothing is upcoming, because
    predicting yesterday is worse than predicting nothing.
    """
    now = now or datetime.now(UTC)

    upcoming = sorted(
        (f for f in live_fixtures if f.kickoff_utc > now),
        key=lambda f: f.kickoff_utc,
    )
    if not upcoming:
        return []

    # The next cluster, not the rest of the season.
    cutoff = upcoming[0].kickoff_utc + ROUND_WINDOW
    round_fixtures = [f for f in upcoming if f.kickoff_utc <= cutoff]

    by_clubs: dict[tuple[str, str], list[dict]] = {}
    for row in enrichment:
        by_clubs.setdefault(_key(row["home_team_raw"], row["away_team_raw"]), []).append(row)

    out = []
    for fixture in round_fixtures:
        extra = _closest(by_clubs.get(_key(fixture.home, fixture.away), []), fixture.kickoff_utc)
        out.append(
            {
                "home_team_raw": fixture.home,
                "away_team_raw": fixture.away,
                "kickoff_utc": fixture.kickoff_utc,
                "known_at": now,
                "referee_raw": (extra or {}).get("referee_raw"),
                "odds_home": (extra or {}).get("odds_home"),
                "odds_draw": (extra or {}).get("odds_draw"),
                "odds_away": (extra or {}).get("odds_away"),
                "source": "pulselive+football-data" if extra else "pulselive",
            }
        )
    return out


def _closest(candidates: list[dict], kickoff: datetime) -> dict | None:
    """The candidate nearest this kickoff, if any is near enough."""
    near = [row for row in candidates if abs(row["kickoff_utc"] - kickoff) <= KICKOFF_SLACK]
    if not near:
        return None
    return min(near, key=lambda row: abs(row["kickoff_utc"] - kickoff))


def fetch(now: datetime | None = None) -> list[dict]:
    """The next round from live sources, falling back to football-data alone.

    The fallback matters: if the league's API is unreachable we would rather
    publish football-data's round, even a stale one, than publish nothing. It is
    reported rather than silent so the difference is visible.
    """
    from foulgorithm.identity.teams import from_pulselive
    from foulgorithm.sources import football_data

    # football-data only DECORATES the round with referees and odds. Between
    # rounds its file is empty and the adapter raises; that must never stop
    # the league's own list deciding the round, least of all at T-60 on a
    # matchday with the confirmed elevens waiting to be published.
    try:
        enrichment = football_data.fetch_fixtures()
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        print(f"  football-data unavailable, referees and odds left unknown: {exc}")
        enrichment = []

    try:
        from foulgorithm.sources import pulselive

        live = [
            type(
                "LiveFixture",
                (),
                {
                    "home": from_pulselive(f.home),
                    "away": from_pulselive(f.away),
                    "kickoff_utc": f.kickoff_utc,
                },
            )()
            for f in pulselive.fixtures()
            if not f.complete
        ]
    except Exception as exc:  # noqa: BLE001 - reported, never silently wrong
        print(f"  league fixture list unavailable, using football-data alone: {exc}")
        return enrichment

    chosen = select(live, enrichment, now)
    if not chosen:
        print("  no upcoming fixtures in the league's list")
    return chosen
