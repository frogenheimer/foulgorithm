"""Did a confirmed eleven make it into the record BEFORE kickoff?

The one question that decides whether the lineup component did its job, asked
after every settle so a silent failure is loud within hours, not weeks."""

from foulgorithm.jobs import lineup_audit


def claim(fixture, published, kickoff, confirmed):
    return {
        "fixture": fixture,
        "published_at": published,
        "kickoff": kickoff,
        "lineup_confirmed": confirmed,
        "model_id": "house",
    }


class TestCoverage:
    def test_a_confirmed_claim_before_kickoff_covers_the_fixture(self):
        rows = [claim("A v B", "2026-08-28T18:41:00+00:00", "2026-08-28T19:00:00+00:00", True)]
        assert lineup_audit.coverage(rows, ["A v B"]) == {"A v B": "2026-08-28T18:41:00+00:00"}

    def test_a_confirmed_claim_after_kickoff_does_not_count(self):
        rows = [claim("A v B", "2026-08-28T19:05:00+00:00", "2026-08-28T19:00:00+00:00", True)]
        assert lineup_audit.coverage(rows, ["A v B"]) == {"A v B": None}

    def test_predicted_claims_never_count(self):
        rows = [claim("A v B", "2026-08-28T12:00:00+00:00", "2026-08-28T19:00:00+00:00", False)]
        assert lineup_audit.coverage(rows, ["A v B"]) == {"A v B": None}

    def test_the_report_names_the_misses(self):
        rows = [claim("A v B", "2026-08-28T18:41:00+00:00", "2026-08-28T19:00:00+00:00", True)]
        text = lineup_audit.report(rows, ["A v B", "C v D"])
        assert "1 of 2" in text and "C v D" in text
