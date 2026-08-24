"""One command per gameweek: refresh, settle, predict, verify, commit, push.

The design in docs/35-weekly-updater.md. Stages run in order, the run stops
at the first hard failure, and nothing reaches git unless the verification
gate passed. The gate asks about outputs and inputs, never about exit codes,
because settle legitimately exits "nothing new" and "deferring", and neither
means the data is fresh.

Two flags, both off by default:

    DRY=1  runs refresh, settle (dry), predict and verify, then prints what
           WOULD be committed and stops. Predict writes real files either
           way, they are deterministic outputs and the claims store dedupes;
           dry mode's promise is only that nothing reaches git.
    PUSH=1 pushes after a successful commit. Off until the updater has
           earned trust over a few clean weeks, because the site is the
           public track record and one bad Saturday published automatically
           costs more than a week of pushes done by hand.

Run with:

    make gameweek            # commit, no push
    make gameweek DRY=1      # rehearse
    make gameweek PUSH=1     # the full loop
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PLAYERS_JSON = Path("site/public/data/players.json")

#: What a publish run is allowed to commit. data/raw is gitignored and stays
#: local; everything here is part of the public record.
COMMIT_PATHS = (
    "site/public/data",
    "data/predictions",
    "data/picks",
    "data/state",
    "data/graded",
    "data/settled",
)

#: Verification ceilings and floors. Bounds, not targets: crossing one means
#: something upstream changed shape and a person should look before the site
#: does.
MAX_EVIDENCE_ANOMALIES = 10
MAX_UNRESOLVED_EVIDENCE = 2500
MIN_PLAYERS_JSON_BYTES = 10_000


@dataclass
class Stage:
    name: str
    ok: bool
    summary: str
    hard: bool = True


# ---------------------------------------------------------------- the checks


def check_file_fresh(path: Path, since: datetime) -> str | None:
    """A publish output this run did not touch is a publish that did not run."""
    if not path.exists():
        return f"{path} does not exist"
    written = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if written < since:
        return f"{path} was last written {written:%Y-%m-%d %H:%M}, before this run"
    return None


def check_players_file(path: Path, fixtures: list[dict]) -> list[str]:
    """Schema-light checks on the site's main payload.

    Deliberately shallow: the deep contract belongs to the publisher's own
    tests. What the gate must catch is a payload that is missing, truncated,
    or silent about a fixture we are supposed to be predicting.
    """
    if not path.exists():
        return [f"{path} does not exist"]
    text = path.read_text()
    if len(text) < MIN_PLAYERS_JSON_BYTES:
        return [f"{path} is {len(text)} bytes, which is not a round of predictions"]
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path} is not valid JSON: {exc}"]

    failures = []
    for fixture in fixtures:
        home = str(fixture.get("home_team_raw") or fixture.get("home") or "")
        if home and home not in text:
            failures.append(f"fixture {home} is missing from {path.name}")
    return failures


def check_evidence_report(report: dict) -> list[str]:
    """The season-evidence build ran inside predict; its report is the tell."""
    if not report:
        return ["no season-evidence report: the blend did not run"]
    failures = []
    if report.get("rows", 0) == 0:
        failures.append("season evidence produced zero rows")
    if report.get("anomalies", 0) > MAX_EVIDENCE_ANOMALIES:
        failures.append(
            f"{report['anomalies']} evidence anomalies, ceiling {MAX_EVIDENCE_ANOMALIES}: "
            "identity or season scope has shifted"
        )
    if report.get("unresolved", 0) > MAX_UNRESOLVED_EVIDENCE:
        failures.append(
            f"{report['unresolved']} unresolved evidence names, ceiling "
            f"{MAX_UNRESOLVED_EVIDENCE}"
        )
    return failures


def commit_message(fixtures: list[dict], skipped: list[str]) -> str:
    """Says what went out, and names what did not."""
    when = datetime.now(timezone.utc)
    head = f"Publish the round: {len(fixtures)} fixtures, {when:%d %b %Y}"
    if not skipped:
        return head
    body = "Skipped, reported and continuing without: " + ", ".join(skipped) + "."
    return f"{head}\n\n{body}"


# ---------------------------------------------------------------- the stages


def refresh_stage() -> Stage:
    """Refresh the running season's match file, and never block on upstream.

    Early in a season football-data has not published the file yet, HTTP 300,
    and no run of ours changes that. Halting the whole gameweek over it would
    mean no predictions at all in August, which is worse than opponent
    context running to the newest file on disk. So upstream unavailability is
    loud and soft: named in every run summary, never a stop. The dry run of
    2026-08-24 hit exactly this and was, correctly, stopped by the old
    behaviour; this is the correction.
    """
    from foulgorithm.sources import football_data
    from foulgorithm.sources.base import SourceError

    try:
        refreshed = football_data.refresh_in_progress()
    except SourceError as exc:
        return Stage(
            "refresh", True,
            f"upstream has no current file yet ({exc}); opponent context runs "
            "to the newest file on disk",
        )
    except Exception as exc:  # noqa: BLE001 - anything else is genuinely broken
        return Stage("refresh", False, f"match data refresh failed: {exc}")
    label = ", ".join(refreshed) if refreshed else "already fresh"
    return Stage("refresh", True, f"match data {label}")


def settle_stage(dry_run: bool) -> Stage:
    from foulgorithm.jobs import settle

    code = settle.run(dry_run=dry_run)
    if code == 2:
        return Stage("settle", False, "season totals unavailable, the source is dead")
    summary = "graded new results" if code == 0 else "nothing new to grade, or deferring"
    return Stage("settle", True, summary)


def predict_stage() -> list[Stage]:
    """The publishers, hard ones first. A cosmetic failure is reported and
    counted, never silently absorbed: the commit message will name it."""
    from foulgorithm.publish import character_round, player_round, predict_round, site_export

    stages = []
    # Each publisher names its own entry point, so the callable is looked up
    # rather than assumed: site_export exports and predict_round predicts,
    # and a rename there should fail the wiring test, never a Saturday run.
    for name, runner, hard in (
        ("predict-matches", predict_round.predict_round, True),
        ("predict-players", player_round.publish, True),
        ("site-overview", site_export.export, False),
        ("character-picks", character_round.publish, False),
    ):
        try:
            runner()
            stages.append(Stage(name, True, "published", hard=hard))
        except Exception as exc:  # noqa: BLE001 - named in the summary and the commit
            stages.append(Stage(name, False, f"failed: {exc}", hard=hard))
    return stages


def verify_stage(run_start: datetime, fixtures: list[dict]) -> Stage:
    from foulgorithm.features import season_totals

    failures = []
    stale = check_file_fresh(PLAYERS_JSON, run_start)
    if stale:
        failures.append(stale)
    failures.extend(check_players_file(PLAYERS_JSON, fixtures))
    failures.extend(check_evidence_report(season_totals.last_report()))

    if failures:
        return Stage("verify", False, "; ".join(failures))
    return Stage("verify", True, f"{len(fixtures)} fixtures verified")


def commit_stage(fixtures: list[dict], skipped: list[str]) -> Stage:
    # Only paths that exist: git add fails whole on a pathspec that matches
    # nothing, and data/settled does not exist until the first settle run
    # after the retention change writes it. That exact case failed a publish
    # at the last stage on 2026-08-24, after every gate had passed.
    present = [p for p in COMMIT_PATHS if Path(p).exists()]
    subprocess.run(["git", "add", "--", *present], check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        return Stage("commit", True, "nothing changed, nothing to commit")
    subprocess.run(["git", "commit", "-m", commit_message(fixtures, skipped)], check=True)
    return Stage("commit", True, "committed")


def push_stage() -> Stage:
    subprocess.run(["git", "pull", "--rebase", "--autostash"], check=True)
    subprocess.run(["git", "push"], check=True)
    return Stage("push", True, "pushed")


# ------------------------------------------------------------------- the run


def run(dry_run: bool = False, push: bool = False) -> int:
    from foulgorithm.features import next_round

    run_start = datetime.now(timezone.utc)
    stages: list[Stage] = []

    def halt() -> int:
        report(stages)
        print("\nstopped at the first hard failure. Nothing was committed.")
        return 1

    stages.append(refresh_stage())
    if not stages[-1].ok:
        return halt()

    stages.append(settle_stage(dry_run))
    if not stages[-1].ok:
        return halt()

    fixtures = next_round.fetch()
    if not fixtures:
        stages.append(Stage("fixtures", True, "no upcoming fixtures, nothing to predict"))
        report(stages)
        return 0

    predict = predict_stage()
    stages.extend(predict)
    if any(not s.ok and s.hard for s in predict):
        return halt()
    skipped = [s.name for s in predict if not s.ok]

    stages.append(verify_stage(run_start, fixtures))
    if not stages[-1].ok:
        return halt()

    if dry_run:
        would = subprocess.run(
            ["git", "status", "--short", "--", *COMMIT_PATHS],
            capture_output=True, text=True, check=False,
        ).stdout
        report(stages)
        print("\nDRY RUN. Would commit:\n" + (would or "  nothing changed\n"))
        return 0

    stages.append(commit_stage(fixtures, skipped))
    if push:
        stages.append(push_stage())
    else:
        stages.append(Stage("push", True, "held: run with PUSH=1 when trusted", hard=False))

    report(stages)
    return 0


def report(stages: list[Stage]) -> None:
    print(f"\n{'stage':<18}{'result':<8}summary")
    print("-" * 60)
    for stage in stages:
        print(f"{stage.name:<18}{'ok' if stage.ok else 'FAILED':<8}{stage.summary}")


def main() -> None:
    dry_run = os.environ.get("DRY") == "1" or "--dry-run" in sys.argv
    push = os.environ.get("PUSH") == "1" or "--push" in sys.argv
    raise SystemExit(run(dry_run=dry_run, push=push))


if __name__ == "__main__":
    main()
