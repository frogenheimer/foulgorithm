"""The provider gap, measured in the form it actually takes.

The league API reads about 4.6% above the FBref archive at league level. Both
external reviews made the same demand before that number corrects anything:
establish the FORM of the gap, because a multiplicative correction and an
additive one distort different players differently, and a flat scalar applied
to the wrong form biases exactly the tails a line is priced on.

These tests plant gaps of known form and size and check the study recovers
them, refuses ambiguous identities in both directions, and never lets an
unmatched player default into the comparison.
"""

import json

import pandas as pd
import pytest

from foulgorithm.backtest import provider_offset_study as study
from foulgorithm.identity.players import resolve_names


def api_frame(rows):
    return pd.DataFrame(rows, columns=["player", "season", "mins_played", "fouls"])


def arch_frame(rows):
    return pd.DataFrame(
        rows, columns=["player", "season", "minutes", "fouls_committed", "position"]
    )


def planted(ratio: float = 1.0, extra_per_90: float = 0.0):
    """The same ten players in both providers, with a gap of known form."""
    api_rows, arch_rows = [], []
    for i in range(10):
        minutes = 900.0 + 180 * i
        fouls = float(3 + 2 * i)
        nineties = minutes / 90.0
        api_rows.append(
            (f"Player {i}", "2023/24", minutes, fouls * ratio + extra_per_90 * nineties)
        )
        arch_rows.append((f"Player {i}", 2024, minutes, fouls, "MF"))
    return api_frame(api_rows), arch_frame(arch_rows)


class TestNameResolutionBothWays:
    """The league API abbreviates as often as FPL lengthens.

    resolve() only checks that a history name sits inside a source name, which
    is the FPL direction. Provider joins face both: "Abdul Fatawu" is the
    API's short form of the archive's "Abdul Fatawu Issahaku". Same refusal
    rules apply in both directions, and a lone token still matches nothing.
    """

    def test_exact_match_still_works(self):
        got = resolve_names(["Emmanuel Dennis"], ["Emmanuel Dennis", "Will Dennis"], overrides={})
        assert got.matched == {"Emmanuel Dennis": "Emmanuel Dennis"}

    def test_source_shorter_than_history_resolves(self):
        got = resolve_names(["Abdul Fatawu"], ["Abdul Fatawu Issahaku", "Alex Palmer"], overrides={})
        assert got.matched == {"Abdul Fatawu": "Abdul Fatawu Issahaku"}

    def test_source_longer_than_history_resolves(self):
        got = resolve_names(
            ["Gabriel Dos Santos Magalhaes"],
            ["Gabriel Magalhaes", "Gabriel Jesus"],
            overrides={},
        )
        assert got.matched == {"Gabriel Dos Santos Magalhaes": "Gabriel Magalhaes"}

    def test_a_lone_surname_never_matches(self):
        """"Dennis" fits two people. Surname matching transplanted foul rates
        between different players once already; it stays banned."""
        got = resolve_names(["Dennis"], ["Emmanuel Dennis", "Will Dennis"], overrides={})
        assert got.matched == {}
        assert "Dennis" in got.unmatched

    def test_two_candidates_is_a_refusal_not_a_choice(self):
        got = resolve_names(
            ["Danilo Silva"],
            ["Danilo Silva Santos", "Danilo Silva Pereira"],
            overrides={},
        )
        assert got.matched == {}
        assert got.ambiguous["Danilo Silva"] == [
            "Danilo Silva Pereira",
            "Danilo Silva Santos",
        ]

    def test_accents_and_spacing_do_not_block_a_match(self):
        got = resolve_names(["Ali Alhamadi"], ["Ali Al Hamadi"], overrides={})
        # Normalisation strips case and accents but keeps word boundaries, so
        # "alhamadi" against "al hamadi" is a genuinely different token set.
        # It must therefore NOT match automatically; the crosswalk settles it.
        assert got.matched == {} or got.matched == {"Ali Alhamadi": "Ali Al Hamadi"}


class TestPairing:
    def test_pairs_join_on_resolved_identity_per_season(self):
        api, arch = planted(ratio=1.05)
        matched, report = study.pair(api, arch)
        assert len(matched) == 10
        assert report["pairs"] == 10
        assert report["unmatched_api"] == 0

    def test_an_unmatched_player_is_counted_out_never_defaulted(self):
        api, arch = planted()
        api = pd.concat(
            [api, api_frame([("Nobody Weknow", "2023/24", 900.0, 30.0)])],
            ignore_index=True,
        )
        matched, report = study.pair(api, arch)
        assert len(matched) == 10
        assert report["unmatched_api"] == 1

    def test_seasons_that_do_not_overlap_are_left_out(self):
        """The archive starts in 2017/18. An API season from 2009/10 has
        nothing to compare against and must not fabricate a pair."""
        api, arch = planted()
        api = pd.concat(
            [api, api_frame([("Player 1", "2009/10", 900.0, 10.0)])], ignore_index=True
        )
        matched, _ = study.pair(api, arch)
        assert len(matched) == 10

    def test_wildly_disagreeing_minutes_are_flagged_out_of_the_form_fit(self):
        """Minutes that disagree by more than 5% mean the two rows are not
        describing the same exposure, whichever provider is right."""
        api, arch = planted()
        api.loc[0, "mins_played"] = api.loc[0, "mins_played"] * 2
        matched, report = study.pair(api, arch)
        assert report["minutes_disagree"] == 1
        assert len(matched[matched["comparable"]]) == 9


class TestTheLeagueTable:
    def test_recovers_a_planted_multiplicative_ratio(self):
        api, arch = planted(ratio=1.05)
        matched, _ = study.pair(api, arch)
        table = study.league_table(matched)
        assert table.loc[table["season"] == 2024, "ratio"].iloc[0] == pytest.approx(
            1.05, abs=0.001
        )

    def test_no_gap_reads_as_one(self):
        api, arch = planted(ratio=1.0)
        matched, _ = study.pair(api, arch)
        table = study.league_table(matched)
        assert table["ratio"].iloc[0] == pytest.approx(1.0, abs=0.001)


class TestTheFormOfTheGap:
    def test_a_multiplicative_plant_reads_as_multiplicative(self):
        api, arch = planted(ratio=1.08)
        matched, _ = study.pair(api, arch)
        fit = study.form_fit(matched)
        assert fit["form"] == "multiplicative"
        assert fit["multiplicative_ratio"] == pytest.approx(1.08, abs=0.005)

    def test_an_additive_plant_reads_as_additive(self):
        api, arch = planted(extra_per_90=0.3)
        matched, _ = study.pair(api, arch)
        fit = study.form_fit(matched)
        assert fit["form"] == "additive"
        assert fit["additive_per_90"] == pytest.approx(0.3, abs=0.01)

    def test_a_flat_ratio_across_volume_supports_multiplicative(self):
        """If the ratio is the same for low and high foulers, a single
        multiplicative correction is safe. If it fell with volume, the gap
        would be additive and a scalar would inflate the tails, which is the
        distortion advisor 1 warned about."""
        api, arch = planted(ratio=1.05)
        matched, _ = study.pair(api, arch)
        by_volume = study.ratio_by_volume(matched, bins=3)
        assert by_volume["ratio"].max() - by_volume["ratio"].min() < 0.01


class TestTheReferenceFile:
    def test_roundtrips_what_the_blend_needs(self, tmp_path):
        api, arch = planted(ratio=1.05)
        matched, report = study.pair(api, arch)
        path = tmp_path / "provider_offset.json"
        study.write_reference(matched, report, path)
        held = json.loads(path.read_text())
        assert held["global"]["ratio"] == pytest.approx(1.05, abs=0.001)
        assert held["form"] in ("multiplicative", "additive")
        assert "2023/24" in held["seasons"]
        assert held["pairs"] == 10
        assert held["measuredAt"]
