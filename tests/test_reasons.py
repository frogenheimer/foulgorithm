"""Every pick explains itself, in the voice of whoever made it.

A probability with no sentence attached asks the reader to trust a number from
a model they cannot see. The sentence is generated from the same `why` block
the number came from, so it cannot drift away from the maths: if it says the
matchup drove the pick, the matchup drove the pick.

Two rules hold across all five voices, and the tests enforce both:

  - **Only true things.** Every claim traces to a figure in `why`. Character is
    in the phrasing, never in the facts.
  - **Thin evidence is said out loud**, in the voice. Terror frets about it and
    Bravery relishes it, and neither is allowed to hide it.
"""

import re

import pytest

from foulgorithm.characters import reasons

CIDS = [
    "alan",
    "lily",
    "valentina",
    "tayler",
    "bdog",
    "pax",
    "justine",
    "mabel",
    "dottie",
    "dele",
    "ian",
]


def leg(**kw):
    base = {
        "player": "Havertz",
        "team": "Arsenal",
        "fixture": "Arsenal v Coventry",
        "market": "committed",
        "line": 0.5,
        "fouls": 1,
        "prob": 0.64,
        "packProb": 0.58,
        "edge": 0.06,
        "thin": False,
    }
    base.update(kw)
    return base


def why(**kw):
    base = {
        "ratePer90": 1.27,
        "expectedMinutes": 85.0,
        "expected_fouls": 1.78,
        "opponentFactor": 1.38,
        "headToHeadFactor": 1.0,
        "refereeFactor": 1.0,
        "effectiveMatches": 38.0,
        "startProbability": 1.0,
        "minutesIfStarting": 85.0,
    }
    base.update(kw)
    return base


class TestEveryVoiceSpeaks:
    @pytest.mark.parametrize("cid", CIDS)
    def test_a_reason_is_produced(self, cid):
        text = reasons.reason(cid, leg(), why())
        assert text and isinstance(text, str)

    @pytest.mark.parametrize("cid", CIDS)
    def test_it_is_one_or_two_sentences_not_an_essay(self, cid):
        text = reasons.reason(cid, leg(), why())
        assert len(text) <= 200, f"too long for a card: {text}"
        assert text[0].isupper() or text[0].isdigit(), f"odd opening: {text}"
        assert text.rstrip()[-1] in ".!?"

    @pytest.mark.parametrize("cid", CIDS)
    def test_it_quotes_a_real_figure(self, cid):
        """No vibes-only sentences. Something in it must be checkable."""
        text = reasons.reason(cid, leg(), why())
        assert re.search(r"\d", text), f"no number anywhere: {text}"

    def test_the_five_do_not_say_the_same_thing(self):
        said = {reasons.reason(cid, leg(), why()) for cid in CIDS}
        assert len(said) == len(CIDS), "if the voices collapse, the characters are decoration"

    @pytest.mark.parametrize("cid", CIDS)
    def test_no_em_dashes(self, cid):
        assert "—" not in reasons.reason(cid, leg(), why())


class TestItTracksTheEvidence:
    """The sentence changes when the numbers change. Otherwise it is wallpaper."""

    def test_a_hostile_matchup_is_noticed(self):
        mild = reasons.reason("valentina", leg(), why(opponentFactor=1.01))
        hostile = reasons.reason("valentina", leg(), why(opponentFactor=1.45))
        assert mild != hostile

    def test_standing_apart_from_the_pack_is_noticed(self):
        alone = reasons.reason("bdog", leg(prob=0.70, packProb=0.52, edge=0.18), why())
        agreed = reasons.reason("bdog", leg(prob=0.60, packProb=0.595, edge=0.005), why())
        assert alone != agreed

    @pytest.mark.parametrize("cid", CIDS)
    def test_thin_evidence_is_never_hidden(self, cid):
        text = reasons.reason(cid, leg(thin=True), why(effectiveMatches=1.2))
        assert text != reasons.reason(cid, leg(thin=False), why(effectiveMatches=38.0))

    @pytest.mark.parametrize("cid", CIDS)
    def test_a_substitute_is_not_described_as_a_starter(self, cid):
        text = reasons.reason(cid, leg(), why(startProbability=0.35, expectedMinutes=28.0))
        assert (
            "start" not in text.lower()
            or "unlikely" in text.lower()
            or "off the bench" in text.lower()
        )

    @pytest.mark.parametrize("cid", CIDS)
    def test_nobody_claims_certainty(self, cid):
        for p in (0.95, 0.64, 0.31):
            text = reasons.reason(cid, leg(prob=p), why()).lower()
            for banned in ("guaranteed", "certain", "nailed on", "can't lose", "cannot lose"):
                assert banned not in text, f"{cid} claimed certainty: {text}"


class TestVoicesAreDistinct:
    """Each lens should show up in the words, not only in the numbers."""

    def test_terror_hedges(self):
        text = reasons.reason("tayler", leg(), why()).lower()
        assert any(
            w in text for w in ("if", "but", "enough", "rather", "least", "still", "which is")
        )

    def test_bravery_references_the_others(self):
        text = reasons.reason("bdog", leg(prob=0.70, packProb=0.52, edge=0.18), why()).lower()
        assert any(w in text for w in ("everyone", "others", "rest", "crowd", "alone", "pack"))

    def test_anger_is_short(self):
        assert len(reasons.reason("alan", leg(), why())) <= 130


class TestUnknownCharacter:
    def test_it_raises_rather_than_inventing_a_voice(self):
        with pytest.raises(KeyError):
            reasons.reason("kevin", leg(), why())


class TestTheTwoKindsOfThin:
    """One upstream flag covers two different problems and they need different words.

    `thin` is set either by too little playing time or by a record that would
    not join to the player at all. Two of thirteen picks in a real round were
    the second kind, one of them with 65.6 effective matches behind it. Calling
    that "not enough matches" is false in a way a reader can catch.
    """

    @pytest.mark.parametrize("cid", CIDS)
    def test_plenty_of_evidence_is_never_called_insufficient(self, cid):
        text = reasons.reason(cid, leg(thin=True), why(effectiveMatches=65.6)).lower()
        assert "65.6 matches" not in text or "not enough" not in text
        assert "0 matches" not in text

    @pytest.mark.parametrize("cid", CIDS)
    def test_a_fraction_of_a_match_does_not_read_as_none(self, cid):
        text = reasons.reason(cid, leg(thin=True), why(effectiveMatches=0.2))
        assert "0 matches" not in text, f"reads as never played: {text}"

    @pytest.mark.parametrize("cid", CIDS)
    def test_the_two_causes_read_differently(self, cid):
        few = reasons.reason(cid, leg(thin=True), why(effectiveMatches=1.2))
        unmatched = reasons.reason(cid, leg(thin=True), why(effectiveMatches=65.6))
        assert few != unmatched


def test_the_thin_threshold_matches_the_publisher():
    """The flag is set there and interpreted here, so the numbers must agree.

    At 5.0 against 8.0 a pick with 5.2 matches was flagged thin upstream and
    read here as "plenty of evidence, unmatchable record", which is a different
    claim about a different problem.
    """
    from foulgorithm.publish import player_round

    assert reasons.THIN_MATCHES == player_round.THIN_EVIDENCE
