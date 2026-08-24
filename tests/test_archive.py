"""Played fixtures keep their pages.

The site only ever generated pages for the round in the current payload, so
a game's page vanished at the first publish after its kickoff, and the picks
that were on it could never be checked against what happened. The archive
fixes that: every publish writes each fixture's page data to its own file,
settle marks the ladder legs with outcomes, and the page outlives the round.
The rules worth pinning: the slug must match the site's exactly or the link
404s, a later pre-kickoff publish replaces an earlier one but a post-kickoff
one never does, and marking outcomes never touches what was published.
"""

import json

from foulgorithm.publish import archive


def payload(label="Fulham v Chelsea", generated="2026-08-24T17:00:00+00:00"):
    return {
        "generatedAt": generated,
        "board": [
            {
                "home": label.split(" v ")[0],
                "away": label.split(" v ")[1],
                "kickoff": "2026-08-24T19:00:00+00:00",
                "referee": "Michael Oliver",
            }
        ],
        "picks": [{"id": "alan", "name": "Alan", "emotion": "calm"}],
        "fixtureSlips": {
            label: {
                "alan": [
                    {
                        "targetLabel": "2/1",
                        "legs": [
                            {
                                "player": "Berge",
                                "fullName": "Sander Berge",
                                "market": "committed",
                                "line": 0.5,
                                "fouls": 1,
                            }
                        ],
                    }
                ]
            }
        },
        "formations": {label: {"Fulham": {"lines": []}}},
        "explorer": {
            "models": ["alan"],
            "lines": [0.5],
            "markets": ["committed"],
            "house": "house",
            "rows": [
                {"player": "Berge", "fullName": "Sander Berge", "fixture": label},
                {"player": "Saliba", "fullName": "William Saliba", "fixture": "Arsenal v Coventry"},
            ],
        },
    }


class TestSlugs:
    def test_the_slug_matches_the_site_exactly(self):
        assert archive.fixture_slug("Fulham v Chelsea") == "fulham-v-chelsea"
        assert archive.fixture_slug("Nott'm Forest v Leeds") == "nott-m-forest-v-leeds"
        assert archive.fixture_slug("Man United v Ipswich") == "man-united-v-ipswich"


class TestTheSlice:
    def test_a_slice_carries_only_its_own_fixture(self):
        s = archive.slice_payload(payload(), "Fulham v Chelsea")
        assert s["label"] == "Fulham v Chelsea"
        assert s["kickoff"] == "2026-08-24T19:00:00+00:00"
        assert s["referee"] == "Michael Oliver"
        assert list(s["ladder"]) == ["alan"]
        rows = s["explorer"]["rows"]
        assert [r["player"] for r in rows] == ["Berge"]
        assert s["characters"] == [{"id": "alan", "name": "Alan"}]

    def test_a_missing_fixture_slices_to_nothing(self):
        assert archive.slice_payload(payload(), "A v B") is None


class TestWriting:
    def test_a_later_pre_kickoff_publish_replaces_an_earlier_one(self, tmp_path):
        archive.write_round(payload(generated="2026-08-24T15:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        archive.write_round(payload(generated="2026-08-24T17:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        held = json.loads((tmp_path / "fulham-v-chelsea.json").read_text())
        assert held["publishedAt"] == "2026-08-24T17:00:00+00:00"

    def test_a_post_kickoff_publish_never_replaces_the_binding_one(self, tmp_path):
        archive.write_round(payload(generated="2026-08-24T17:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        archive.write_round(payload(generated="2026-08-24T21:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        held = json.loads((tmp_path / "fulham-v-chelsea.json").read_text())
        assert held["publishedAt"] == "2026-08-24T17:00:00+00:00"

    def test_a_fixture_only_ever_seen_post_kickoff_gets_no_page(self, tmp_path):
        archive.write_round(payload(generated="2026-08-24T21:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        assert not (tmp_path / "fulham-v-chelsea.json").exists()

    def test_the_head_to_head_survives_the_sheet_rolling_on(self, tmp_path):
        sheet = {
            "window": 5,
            "seasons": ["2025-26"],
            "note": "n",
            "fixtures": [{"home": "Fulham", "away": "Chelsea", "teams": {}}],
        }
        archive.write_round(
            payload(generated="2026-08-24T15:00:00+00:00"), root=tmp_path, matchday=sheet
        )
        archive.write_round(
            payload(generated="2026-08-24T17:00:00+00:00"),
            root=tmp_path,
            matchday={"fixtures": []},
        )
        held = json.loads((tmp_path / "fulham-v-chelsea.json").read_text())
        assert held["matchday"]["fixture"]["home"] == "Fulham"

    def test_marking_survives_a_rewrite(self, tmp_path):
        archive.write_round(payload(generated="2026-08-24T15:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        path = tmp_path / "fulham-v-chelsea.json"
        held = json.loads(path.read_text())
        held["outcomes"] = {"Sander Berge|committed|0.5": {"won": False, "observed": 0}}
        path.write_text(json.dumps(held))
        archive.write_round(payload(generated="2026-08-24T17:00:00+00:00"), root=tmp_path, matchday={"fixtures": []})
        held = json.loads(path.read_text())
        assert held["publishedAt"] == "2026-08-24T17:00:00+00:00"
        assert held["outcomes"]["Sander Berge|committed|0.5"]["won"] is False


class TestOutcomes:
    PREDICTIONS = [
        {
            "key": "abc123",
            "fixture": "Fulham v Chelsea",
            "entity": "Sander Berge",
            "market": "player_fouls_committed",
            "line": 0.5,
        },
        {
            "key": "zzz999",
            "fixture": "Arsenal v Coventry",
            "entity": "William Saliba",
            "market": "player_fouls_committed",
            "line": 0.5,
        },
    ]
    GRADED = [
        {"key": "abc123", "won": False, "observed": 0.0},
        {"key": "zzz999", "won": True, "observed": 2.0},
    ]

    def test_outcomes_are_scoped_to_the_fixture(self):
        out = archive.outcomes_for("Fulham v Chelsea", self.GRADED, self.PREDICTIONS)
        assert out == {"Sander Berge|committed|0.5": {"won": False, "observed": 0.0}}

    def test_marking_attaches_outcomes_and_the_result(self, tmp_path):
        archive.write_round(payload(), root=tmp_path, matchday={"fixtures": []})
        season = [
            {
                "home": "Fulham",
                "away": "Chelsea",
                "status": "C",
                "score": [2.0, 3.0],
                "result": {"home": {"fouls": 9}, "away": {"fouls": 12}},
            }
        ]
        marked = archive.mark_all(
            graded=self.GRADED,
            predictions=self.PREDICTIONS,
            season_fixtures=season,
            root=tmp_path,
        )
        assert marked == 1
        held = json.loads((tmp_path / "fulham-v-chelsea.json").read_text())
        assert held["outcomes"]["Sander Berge|committed|0.5"]["won"] is False
        assert held["result"]["score"] == [2.0, 3.0]

    def test_an_unplayed_fixture_is_left_unmarked(self, tmp_path):
        archive.write_round(payload(), root=tmp_path, matchday={"fixtures": []})
        marked = archive.mark_all(
            graded=[], predictions=[], season_fixtures=[], root=tmp_path
        )
        assert marked == 0
        held = json.loads((tmp_path / "fulham-v-chelsea.json").read_text())
        assert "outcomes" not in held or not held["outcomes"]
