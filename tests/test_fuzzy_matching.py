"""Tests for fuzzy matching functionality in config flow."""

import pytest

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow


@pytest.fixture
def config_flow():
    """Create a config flow instance for testing."""
    return OpenPublicTransportConfigFlow()


def test_fuzzy_match_ratio_exact(config_flow):
    """Test fuzzy matching with exact matches."""
    assert config_flow._fuzzy_match_ratio("Düsseldorf", "Düsseldorf") == 1.0
    assert config_flow._fuzzy_match_ratio("Hauptbahnhof", "Hauptbahnhof") == 1.0


def test_fuzzy_match_ratio_case_insensitive(config_flow):
    """Test fuzzy matching is case insensitive."""
    ratio = config_flow._fuzzy_match_ratio("düsseldorf", "DÜSSELDORF")
    assert ratio == 1.0


def test_fuzzy_match_ratio_similar(config_flow):
    """Test fuzzy matching with similar strings."""
    # Typo: "Dusseldorf" vs "Düsseldorf"
    ratio = config_flow._fuzzy_match_ratio("Dusseldorf", "Düsseldorf")
    assert ratio > 0.8

    # Small typo: "Hauptbanhof" vs "Hauptbahnhof"
    ratio = config_flow._fuzzy_match_ratio("Hauptbanhof", "Hauptbahnhof")
    assert ratio > 0.9


def test_fuzzy_match_ratio_different(config_flow):
    """Test fuzzy matching with different strings."""
    ratio = config_flow._fuzzy_match_ratio("Köln", "Berlin")
    assert ratio < 0.5


def test_levenshtein_distance_identical(config_flow):
    """Test Levenshtein distance with identical strings."""
    assert config_flow._levenshtein_distance("test", "test") == 0
    assert config_flow._levenshtein_distance("Düsseldorf", "Düsseldorf") == 0


def test_levenshtein_distance_one_char(config_flow):
    """Test Levenshtein distance with one character difference."""
    # One substitution
    assert config_flow._levenshtein_distance("test", "tast") == 1

    # One insertion
    assert config_flow._levenshtein_distance("test", "tests") == 1

    # One deletion
    assert config_flow._levenshtein_distance("tests", "test") == 1


def test_levenshtein_distance_multiple(config_flow):
    """Test Levenshtein distance with multiple edits."""
    # Two substitutions: Hauptbanhof -> Hauptbahnhof
    assert config_flow._levenshtein_distance("Hauptbanhof", "Hauptbahnhof") == 1

    # Multiple edits
    assert config_flow._levenshtein_distance("kitten", "sitting") == 3


def test_normalize_umlauts(config_flow):
    """Test umlaut normalization."""
    assert config_flow._normalize_umlauts("Düsseldorf") == "Duesseldorf"
    assert config_flow._normalize_umlauts("Köln") == "Koeln"
    assert config_flow._normalize_umlauts("München") == "Muenchen"
    assert config_flow._normalize_umlauts("Straße") == "Strasse"


def test_calculate_relevance_exact_match(config_flow):
    """Test relevance scoring with exact match."""
    score = config_flow._calculate_relevance("Hauptbahnhof", "Hauptbahnhof", "Düsseldorf")
    # Should have high score for exact match
    assert score > 300


def test_calculate_relevance_typo_tolerance(config_flow):
    """Test relevance scoring with typos."""
    # Small typo should still get good score due to fuzzy matching
    score_typo = config_flow._calculate_relevance("Hauptbanhof", "Hauptbahnhof", "Düsseldorf")
    score_exact = config_flow._calculate_relevance("Hauptbahnhof", "Hauptbahnhof", "Düsseldorf")

    # Typo should score lower than exact, but still reasonably high
    assert score_typo > 200
    assert score_typo < score_exact


def test_calculate_relevance_umlaut_tolerance(config_flow):
    """Test relevance scoring with umlaut variations."""
    # "Dusseldorf" without umlauts should match "Düsseldorf"
    score_no_umlaut = config_flow._calculate_relevance("Dusseldorf", "Düsseldorf", "")
    score_with_umlaut = config_flow._calculate_relevance("Düsseldorf", "Düsseldorf", "")

    # Both should get high scores
    assert score_no_umlaut > 200
    assert score_with_umlaut > 200


def test_calculate_relevance_place_bonus(config_flow):
    """Test relevance scoring with place name matching."""
    # When place is mentioned in search, it should get place bonus
    score = config_flow._calculate_relevance("Düsseldorf Hauptbahnhof", "Hauptbahnhof", "Düsseldorf")

    # Should get place matching bonus (200 points)
    assert score >= 200  # Place match gives +200


def test_calculate_relevance_starts_with(config_flow):
    """Test relevance scoring when name starts with search term."""
    score = config_flow._calculate_relevance("Haupt", "Hauptbahnhof", "Düsseldorf")
    # Should get bonus for starts-with match
    assert score > 150


def test_calculate_relevance_word_matching(config_flow):
    """Test relevance scoring with individual word fuzzy matching."""
    # "Hauptbanhof" is close to "Hauptbahnhof"
    score = config_flow._calculate_relevance("Hauptbanhof Dusseldorf", "Hauptbahnhof", "Düsseldorf")

    # Should get points for fuzzy word matching
    assert score > 100


def test_calculate_relevance_comparison(config_flow):
    """Test relevance scoring ranks results correctly."""
    # Exact match should score highest
    exact = config_flow._calculate_relevance("Hauptbahnhof", "Hauptbahnhof", "Düsseldorf")

    # Starts with should score high
    prefix = config_flow._calculate_relevance("Haupt", "Hauptbahnhof", "Düsseldorf")

    # Small typo should score reasonably (fuzzy matching helps here)
    typo = config_flow._calculate_relevance("Hauptbanhof", "Hauptbahnhof", "Düsseldorf")

    # Very different should score low
    different = config_flow._calculate_relevance("Köln", "Hauptbahnhof", "Düsseldorf")

    # Verify ranking - exact should be highest
    assert exact > prefix
    assert exact > typo
    assert exact > different

    # Both prefix and typo should score reasonably high (fuzzy matching helps typos)
    assert prefix > different
    assert typo > different
    assert different >= 0  # Should never be negative

    # Typo with good fuzzy match can score higher than short prefix
    # This is actually good behavior - user likely meant the full word with typo
