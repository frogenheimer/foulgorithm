"""docs/49: grading reruns from the settled rows on file.

A binding version that arrives after the bot's grade (a hand publish pushed
late, a rebase) used to sit ungraded for the season. Every table refresh now
grades any claim for a completed fixture from the window that covers it.
"""

import json

from foulgorithm.jobs import settle
from foulgorithm.review import grade as grading

WINDOW = {
    "window_start": "2026-08-28T21:12:12+00:00",
    "window_end": "2026-08-29T20:24:30+00:00",
}


def _claim(key, entity, fixture="Tottenham v Newcastle", kickoff="2026-08-29T15:30:00+00:00"):
    return {
        "key": key,
        "entity": entity,
        "market": "player_fouls_committed",
        "line": 0.5,
        "probability": 0.6,
        "model_id": "alan",
        "fixture": fixture,
        "kickoff": kickoff,
    }


def _rows(path, *players):
    with path.open("w") as handle:
        for name, fouls in players:
            handle.write(
                json.dumps({"player": name, "fouls_committed": fouls, "fouls_drawn": 0, **WINDOW})
                + "\n"
            )


def test_an_ungraded_claim_in_a_stored_window_is_graded(tmp_path):
    rows = tmp_path / "player_matches.jsonl"
    _rows(rows, ("Yoane Wissa", 2))
    graded = tmp_path / "graded"
    n = settle.regrade_from_windows(
        {"Tottenham v Newcastle"},
        claims=[_claim("k1", "Yoane Wissa")],
        rows_path=rows,
        graded_root=graded,
    )
    assert n == 1
    got = grading.load_all(graded)
    assert [(g["key"], g["won"], g["observed"]) for g in got] == [("k1", True, 2.0)]


def test_a_second_run_grades_nothing_new(tmp_path):
    rows = tmp_path / "player_matches.jsonl"
    _rows(rows, ("Yoane Wissa", 2))
    graded = tmp_path / "graded"
    claims = [_claim("k1", "Yoane Wissa")]
    settle.regrade_from_windows(
        {"Tottenham v Newcastle"}, claims=claims, rows_path=rows, graded_root=graded
    )
    n = settle.regrade_from_windows(
        {"Tottenham v Newcastle"}, claims=claims, rows_path=rows, graded_root=graded
    )
    assert n == 0
    assert len(grading.load_all(graded)) == 1


def test_a_fixture_outside_every_window_is_left_alone(tmp_path):
    rows = tmp_path / "player_matches.jsonl"
    _rows(rows, ("Yoane Wissa", 2))
    graded = tmp_path / "graded"
    n = settle.regrade_from_windows(
        {"Tottenham v Newcastle"},
        claims=[_claim("k1", "Yoane Wissa", kickoff="2026-09-05T14:00:00+00:00")],
        rows_path=rows,
        graded_root=graded,
    )
    assert n == 0
    assert not graded.exists()


def test_a_player_who_never_featured_stays_ungraded(tmp_path):
    rows = tmp_path / "player_matches.jsonl"
    _rows(rows, ("Yoane Wissa", 2))
    graded = tmp_path / "graded"
    n = settle.regrade_from_windows(
        {"Tottenham v Newcastle"},
        claims=[_claim("k2", "Conor Gallagher")],
        rows_path=rows,
        graded_root=graded,
    )
    assert n == 0


def test_no_rows_on_file_is_not_an_error(tmp_path):
    n = settle.regrade_from_windows(
        {"Tottenham v Newcastle"},
        claims=[_claim("k1", "Yoane Wissa")],
        rows_path=tmp_path / "missing.jsonl",
        graded_root=tmp_path / "graded",
    )
    assert n == 0


class TestNamesAreResolvedBeforeGrading:
    """The league's season totals abbreviate ("Nico González", "Andy
    Robertson") where our claims carry the squad's fuller name. 29 of the 36
    legs that read as no-shows on 30 August were this gap. Outcomes are keyed
    by the claim's own entity, resolved through identity.players, and a name
    the rules refuse stays ungraded rather than guessed."""

    def test_the_token_rule_bridges_a_longer_claim_name(self):
        matches = {"Nico González": {"fouls_committed": 3, "fouls_drawn": 1}}
        claims = [_claim("k1", "Nico González Iglesias")]
        outs = settle.resolve_outcomes(matches, claims, overrides={})
        assert outs[("Nico González Iglesias", "player_fouls_committed")] == 3.0
        assert outs[("Nico González Iglesias", "player_fouls_drawn")] == 1.0

    def test_an_alias_bridges_a_different_forename(self):
        matches = {"Andy Robertson": {"fouls_committed": 1, "fouls_drawn": 0}}
        claims = [_claim("k1", "Andrew Robertson")]
        outs = settle.resolve_outcomes(
            matches, claims, overrides={"andrew robertson": "Andy Robertson"}
        )
        assert outs[("Andrew Robertson", "player_fouls_committed")] == 1.0

    def test_the_shipped_crosswalk_carries_robertson(self):
        matches = {"Andy Robertson": {"fouls_committed": 1, "fouls_drawn": 0}}
        outs = settle.resolve_outcomes(matches, [_claim("k1", "Andrew Robertson")])
        assert ("Andrew Robertson", "player_fouls_committed") in outs

    def test_an_exact_name_still_grades(self):
        matches = {"Yoane Wissa": {"fouls_committed": 2, "fouls_drawn": 2}}
        outs = settle.resolve_outcomes(matches, [_claim("k1", "Yoane Wissa")], overrides={})
        assert outs[("Yoane Wissa", "player_fouls_committed")] == 2.0

    def test_a_surname_alone_never_matches(self):
        matches = {"Emmanuel Dennis": {"fouls_committed": 2, "fouls_drawn": 0}}
        outs = settle.resolve_outcomes(matches, [_claim("k1", "Will Dennis")], overrides={})
        assert ("Will Dennis", "player_fouls_committed") not in outs

    def test_the_regrade_grades_through_the_resolution(self, tmp_path):
        rows = tmp_path / "player_matches.jsonl"
        _rows(rows, ("Nico González", 3))
        graded = tmp_path / "graded"
        n = settle.regrade_from_windows(
            {"Tottenham v Newcastle"},
            claims=[_claim("k1", "Nico González Iglesias")],
            rows_path=rows,
            graded_root=graded,
        )
        assert n == 1
        assert grading.load_all(graded)[0]["observed"] == 3.0
