"""The gameweek updater's gates, which are the whole point of it.

The stages were all runnable by hand before this existed. What was missing
was the discipline between them: stop at the first hard failure, verify the
OUTPUT rather than the exit code, commit only what passed, and name anything
that was skipped. These tests pin that discipline with every stage faked, so
they run offline in milliseconds and the orchestration is what is tested.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from foulgorithm.jobs import gameweek as gw


NOW = datetime.now(timezone.utc)
FIXTURES = [{"home_team_raw": "Arsenal"}, {"home_team_raw": "Leeds"}]


class TestFreshness:
    def test_a_missing_file_is_named(self, tmp_path):
        got = gw.check_file_fresh(tmp_path / "players.json", NOW)
        assert "does not exist" in got

    def test_a_file_from_before_the_run_fails(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text("{}")
        got = gw.check_file_fresh(path, NOW + timedelta(hours=1))
        assert "before this run" in got

    def test_a_file_this_run_wrote_passes(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text("{}")
        assert gw.check_file_fresh(path, NOW - timedelta(hours=1)) is None


class TestPlayersPayload:
    def payload(self, teams=("Arsenal", "Leeds")):
        return json.dumps({"fixtures": [{"home": t, "rows": ["x" * 200] * 30} for t in teams]})

    def test_a_good_payload_passes(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text(self.payload() + " " * gw.MIN_PLAYERS_JSON_BYTES)
        assert gw.check_players_file(path, FIXTURES) == []

    def test_a_truncated_payload_is_caught_by_size(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text('{"fixtures": []}')
        got = gw.check_players_file(path, FIXTURES)
        assert any("bytes" in f for f in got)

    def test_invalid_json_is_caught(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text('{"fixtures": [' + " " * gw.MIN_PLAYERS_JSON_BYTES)
        got = gw.check_players_file(path, FIXTURES)
        assert any("not valid JSON" in f for f in got)

    def test_a_fixture_absent_from_the_payload_is_named(self, tmp_path):
        path = tmp_path / "players.json"
        path.write_text(self.payload(teams=("Arsenal",)) + " " * gw.MIN_PLAYERS_JSON_BYTES)
        got = gw.check_players_file(path, FIXTURES)
        assert got == ["fixture Leeds is missing from players.json"]


class TestEvidenceReport:
    def test_a_healthy_report_passes(self):
        assert gw.check_evidence_report({"rows": 60000, "anomalies": 5, "unresolved": 1800}) == []

    def test_no_report_means_the_blend_did_not_run(self):
        assert gw.check_evidence_report({}) == ["no season-evidence report: the blend did not run"]

    def test_anomalies_over_the_ceiling_are_named(self):
        got = gw.check_evidence_report({"rows": 1, "anomalies": 11, "unresolved": 0})
        assert any("11 evidence anomalies" in f for f in got)


class TestTheCommitMessage:
    def test_says_what_went_out(self):
        assert gw.commit_message(FIXTURES, []).startswith("Publish the round: 2 fixtures")

    def test_names_what_was_skipped(self):
        message = gw.commit_message(FIXTURES, ["site-overview"])
        assert "Skipped" in message and "site-overview" in message


class TestWiring:
    """The stages call real modules by attribute. A rename in a publisher
    must fail here, offline, never on a Saturday. This is the check that
    caught site_export.export and predict_round.predict_round on day one,
    both of which the first draft assumed were called publish."""

    def test_every_stage_dependency_exists_and_is_callable(self):
        from foulgorithm.features import next_round
        from foulgorithm.jobs import settle
        from foulgorithm.publish import (
            character_round,
            player_round,
            predict_round,
            site_export,
        )
        from foulgorithm.sources import football_data

        for fn in (
            football_data.refresh_in_progress,
            settle.run,
            next_round.fetch,
            predict_round.predict_round,
            player_round.publish,
            site_export.export,
            character_round.publish,
        ):
            assert callable(fn)

    def test_settle_accepts_the_dry_run_flag(self):
        import inspect

        from foulgorithm.jobs import settle

        assert "dry_run" in inspect.signature(settle.run).parameters


class TestOrchestration:
    """Every stage faked; only the discipline between them is under test."""

    def wire(self, monkeypatch, **overrides):
        calls = []

        def stage(name, ok=True, hard=True):
            def _run(*args, **kwargs):
                calls.append(name)
                if name == "predict":
                    return [gw.Stage("predict-players", ok, "x", hard=hard)]
                return gw.Stage(name, ok, "x", hard=hard)
            return _run

        monkeypatch.setattr(gw, "refresh_stage", overrides.get("refresh", stage("refresh")))
        monkeypatch.setattr(gw, "settle_stage", overrides.get("settle", stage("settle")))
        monkeypatch.setattr(gw, "predict_stage", overrides.get("predict", stage("predict")))
        monkeypatch.setattr(gw, "verify_stage", overrides.get("verify", stage("verify")))
        monkeypatch.setattr(gw, "commit_stage", overrides.get("commit", stage("commit")))
        monkeypatch.setattr(gw, "push_stage", overrides.get("push", stage("push")))

        import foulgorithm.features.next_round as nr
        monkeypatch.setattr(nr, "fetch", lambda now=None: FIXTURES)
        return calls

    def stage_named(self, name, ok=True, hard=True, as_list=False):
        def _run(*args, **kwargs):
            result = gw.Stage(name, ok, "x", hard=hard)
            return [result] if as_list else result
        return _run

    def test_a_dead_settle_source_stops_before_predict(self, monkeypatch, capsys):
        calls = self.wire(
            monkeypatch, settle=self.stage_named("settle", ok=False)
        )
        assert gw.run() == 1
        assert "predict" not in calls
        assert "commit" not in calls
        assert "Nothing was committed" in capsys.readouterr().out

    def test_a_failed_verify_stops_before_commit(self, monkeypatch, capsys):
        calls = self.wire(
            monkeypatch, verify=self.stage_named("verify", ok=False)
        )
        assert gw.run() == 1
        assert "commit" not in calls

    def test_a_hard_predict_failure_stops_the_run(self, monkeypatch, capsys):
        calls = self.wire(
            monkeypatch,
            predict=self.stage_named("predict-players", ok=False, hard=True, as_list=True),
        )
        assert gw.run() == 1
        assert "verify" not in calls

    def test_a_cosmetic_failure_continues_and_is_skipped_by_name(self, monkeypatch, capsys):
        def predict(*args, **kwargs):
            return [
                gw.Stage("predict-players", True, "x", hard=True),
                gw.Stage("site-overview", False, "x", hard=False),
            ]

        seen = {}

        def commit(fixtures, skipped):
            seen["skipped"] = skipped
            return gw.Stage("commit", True, "x")

        self.wire(monkeypatch, predict=predict, commit=commit)
        assert gw.run() == 0
        assert seen["skipped"] == ["site-overview"]

    def test_dry_run_stops_before_commit(self, monkeypatch, capsys):
        calls = self.wire(monkeypatch)
        assert gw.run(dry_run=True) == 0
        assert "commit" not in calls
        assert "DRY RUN" in capsys.readouterr().out

    def test_push_is_held_unless_asked_for(self, monkeypatch, capsys):
        calls = self.wire(monkeypatch)
        assert gw.run() == 0
        assert "commit" in calls
        assert "push" not in calls
        assert "PUSH=1" in capsys.readouterr().out

    def test_push_runs_when_asked_for(self, monkeypatch, capsys):
        calls = self.wire(monkeypatch)
        assert gw.run(push=True) == 0
        assert "push" in calls


class TestRefreshSoftness:
    """Upstream not having published the current season's file is loud and
    soft, never a stop: halting the gameweek over HTTP 300 means no
    predictions in August. The dry rehearsal of 2026-08-24 hit exactly this."""

    def test_upstream_unavailability_continues_with_a_named_summary(self, monkeypatch):
        from foulgorithm.sources import football_data
        from foulgorithm.sources.base import SourceError

        def unavailable(*a, **k):
            raise SourceError("E0.csv returned HTTP 300")

        monkeypatch.setattr(football_data, "refresh_in_progress", unavailable)
        stage = gw.refresh_stage()
        assert stage.ok
        assert "upstream has no current file yet" in stage.summary

    def test_anything_else_still_stops_the_run(self, monkeypatch):
        from foulgorithm.sources import football_data

        def broken(*a, **k):
            raise RuntimeError("disk full")

        monkeypatch.setattr(football_data, "refresh_in_progress", broken)
        stage = gw.refresh_stage()
        assert not stage.ok
