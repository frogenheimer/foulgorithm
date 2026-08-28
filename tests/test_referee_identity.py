"""One referee, three spellings, and a join that has been silently failing.

football-data writes "A Kitchen". API-Football writes "Andrew Kitchen, England".
The hand-fed cup slate wrote "Andrew Kitchen". features/match_features matches
on the raw string, so the cup tie's referee factor has been finding nothing and
reporting that as "no record" rather than as a bug.

Normalising to first-initial-plus-surname is what football-data already uses,
so it is the target format rather than a new one.
"""

from foulgorithm.identity import referees


class TestNormalise:
    def test_football_datas_own_format_is_unchanged(self):
        assert referees.normalise("A Kitchen") == "A Kitchen"

    def test_a_full_first_name_becomes_an_initial(self):
        assert referees.normalise("Andrew Kitchen") == "A Kitchen"

    def test_api_footballs_country_suffix_is_dropped(self):
        assert referees.normalise("Andrew Kitchen, England") == "A Kitchen"

    def test_a_middle_name_is_dropped_not_kept_as_an_initial(self):
        # football-data writes one initial, so we write one initial.
        assert referees.normalise("Michael Oliver") == "M Oliver"
        assert referees.normalise("Michael A Oliver") == "M Oliver"

    def test_a_double_barrelled_surname_survives_whole(self):
        assert referees.normalise("Sam Barrott-Jones") == "S Barrott-Jones"

    def test_a_surname_with_a_particle_survives_whole(self):
        assert referees.normalise("Robert Van Der Berg") == "R Van Der Berg"

    def test_case_and_spacing_are_tidied(self):
        assert referees.normalise("  andrew   KITCHEN  ") == "A Kitchen"

    def test_an_existing_initial_with_a_dot_loses_the_dot(self):
        assert referees.normalise("A. Kitchen") == "A Kitchen"

    def test_a_surname_alone_is_left_alone(self):
        assert referees.normalise("Kitchen") == "Kitchen"

    def test_nothing_normalises_to_nothing(self):
        assert referees.normalise("") is None
        assert referees.normalise(None) is None


class TestSameReferee:
    def test_the_three_source_spellings_all_agree(self):
        assert referees.same("A Kitchen", "Andrew Kitchen")
        assert referees.same("Andrew Kitchen, England", "A Kitchen")

    def test_two_different_officials_do_not(self):
        assert not referees.same("A Kitchen", "M Oliver")

    def test_two_officials_sharing_an_initial_and_surname_are_treated_as_one(self):
        # Honest limit: initial plus surname cannot separate them, and the
        # crosswalk is where a real collision gets resolved by hand.
        assert referees.same("A Kitchen", "Anthony Kitchen")


class TestDisplayName:
    def test_the_fullest_spelling_we_hold_is_the_one_shown(self):
        # "Andrew Kitchen" reads better than "A Kitchen" on a page, so the
        # long form is kept for display while the short form does the joining.
        assert referees.display("Andrew Kitchen, England") == "Andrew Kitchen"

    def test_an_initialled_name_displays_as_it_arrived(self):
        assert referees.display("A Kitchen") == "A Kitchen"
