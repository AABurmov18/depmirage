from depmirage.typosquat import levenshtein, nearest_popular, POPULAR_SET


def test_levenshtein_basics():
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("abc", "abd") == 1        # substitution
    assert levenshtein("abc", "ab") == 1         # deletion
    assert levenshtein("ab", "abc") == 1         # insertion
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3


def test_levenshtein_symmetry():
    assert levenshtein("requests", "reqeusts") == levenshtein("reqeusts", "requests")


def test_nearest_popular_flags_typo():
    # distance 1: an inserted letter ("requestss") from "requests"
    assert nearest_popular("requestss") == "requests"
    # distance 1: a deleted letter ("reqests") from "requests"
    assert nearest_popular("reqests") == "requests"
    # distance 1: a substituted letter ("numpi") from "numpy"
    assert nearest_popular("numpi") == "numpy"


def test_transposition_is_distance_two_not_flagged():
    # Standard Levenshtein counts a transposition as 2 edits, so a strict
    # distance-1 rule does not flag it as a lookalike (it would still be caught
    # by the existence check if the name is not on PyPI).
    assert nearest_popular("reqeusts") is None


def test_exact_popular_is_not_a_lookalike():
    assert nearest_popular("requests") is None
    assert nearest_popular("numpy") is None
    assert "requests" in POPULAR_SET


def test_distant_name_is_not_flagged():
    assert nearest_popular("my-internal-company-lib-xyz") is None
