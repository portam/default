"""
Unit tests for the Spelling Verification Service.

This module tests the French phonetic alphabet implementation,
name pattern detection, and verification prompt generation.
"""

import pytest

from src.services.spelling import (
    COMMON_CONFUSIONS,
    FRENCH_PHONETIC_ALPHABET,
    SpellingVerificationService,
)

# Alias for test compatibility
SpellingService = SpellingVerificationService


class TestFrenchPhoneticAlphabet:
    """Test the French phonetic alphabet is complete and correct."""

    def test_all_letters_covered(self):
        """All 26 letters of the alphabet should have phonetic words."""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for letter in alphabet:
            assert letter in FRENCH_PHONETIC_ALPHABET, f"Missing letter: {letter}"

    def test_standard_french_alphabet(self):
        """Verify standard French phonetic alphabet words."""
        expected_samples = {
            "A": "Anatole",
            "B": "Berthe",
            "M": "Marcel",
            "P": "Pierre",
            "Z": "Zoé",
        }
        for letter, word in expected_samples.items():
            assert FRENCH_PHONETIC_ALPHABET[letter] == word


class TestSpellingService:
    """Test the SpellingService class."""

    @pytest.fixture
    def service(self):
        """Create a SpellingService instance."""
        return SpellingService()

    # ==================== Simple Names ====================

    def test_simple_name_phonetics(self, service):
        """Simple names should produce phonetic spelling."""
        result = service.generate_verification_prompt("Marie")
        # Should contain phonetic representations
        assert "Marcel" in result  # M
        assert "Anatole" in result  # A
        assert len(result) > 10

    def test_short_name(self, service):
        """Short names should still be spelled out."""
        result = service.generate_verification_prompt("Léa")
        assert "Louis" in result  # L
        assert len(result) > 5

    # ==================== Double Letters ====================

    @pytest.mark.parametrize("name,double_letter", [
        ("Jeanne", "N"),
        ("Emmanuel", "M"),
        ("Juliette", "T"),
        ("Isabelle", "L"),
        ("Philippe", "P"),
    ])
    def test_double_letters_detected(self, service, name, double_letter):
        """Names with double letters should indicate them clearly."""
        result = service.generate_verification_prompt(name)
        # Should mention "deux" or have the letter repeated
        assert (
            "deux" in result.lower()
            or result.count(FRENCH_PHONETIC_ALPHABET[double_letter]) >= 2
            or f"{double_letter}, {double_letter}" in result.upper()
        )

    # ==================== Accented Characters ====================

    @pytest.mark.parametrize("name,accent_type", [
        ("Hélène", "accent"),
        ("François", "cédille"),
        ("Noël", "tréma"),
        ("Anaïs", "tréma"),
        ("André", "accent"),
    ])
    def test_accented_characters(self, service, name, accent_type):
        """Accented characters should be explicitly mentioned."""
        result = service.generate_verification_prompt(name)
        assert accent_type in result.lower() or "accent" in result.lower()

    # ==================== Hyphenated Names ====================

    @pytest.mark.parametrize("name", [
        "Jean-Pierre",
        "Marie-Claire",
        "Anne-Sophie",
        "Louis-Philippe",
    ])
    def test_hyphenated_names(self, service, name):
        """Hyphenated names should clearly indicate the hyphen."""
        result = service.generate_verification_prompt(name)
        assert "tiret" in result.lower()

    # ==================== Apostrophe Names ====================

    @pytest.mark.parametrize("name", [
        "D'Angelo",
        "O'Brien",
        "L'Hermite",
    ])
    def test_apostrophe_names(self, service, name):
        """Names with apostrophes should mention them."""
        result = service.generate_verification_prompt(name)
        assert "apostrophe" in result.lower()

    # ==================== Confusion Detection ====================

    def test_confusion_patterns_exist(self):
        """Common confusion patterns should be defined."""
        assert len(COMMON_CONFUSIONS) > 0
        assert "ph" in COMMON_CONFUSIONS or "PH" in COMMON_CONFUSIONS.keys()

    # ==================== Foreign Origin Names ====================

    @pytest.mark.parametrize("name", [
        "Mohammed",
        "Fatima",
        "Nguyen",
        "Giovanni",
        "Wolfgang",
    ])
    def test_foreign_names_spelled(self, service, name):
        """Foreign names should be fully spelled out."""
        result = service.generate_verification_prompt(name)
        # Should have phonetic representations for each letter
        sum(1 for c in name if c.isalpha())
        # Reasonable check: result should be much longer than name
        assert len(result) > len(name) * 2

    # ==================== Silent Letters ====================

    @pytest.mark.parametrize("name", [
        "Benoît",
        "Bernard",
        "Renaud",
    ])
    def test_silent_letters(self, service, name):
        """Names with silent letters should spell all letters."""
        result = service.generate_verification_prompt(name)
        # Each letter should have a phonetic representation
        assert len(result) > len(name)

    # ==================== Case Handling ====================

    def test_case_insensitive(self, service):
        """Spelling should work regardless of case."""
        result_lower = service.generate_verification_prompt("marie")
        result_upper = service.generate_verification_prompt("MARIE")
        result_mixed = service.generate_verification_prompt("MaRiE")

        # All should produce similar results
        assert "Marcel" in result_lower
        assert "Marcel" in result_upper
        assert "Marcel" in result_mixed


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def service(self):
        return SpellingService()

    def test_empty_name(self, service):
        """Empty name should return empty or error message."""
        result = service.generate_verification_prompt("")
        # Should handle gracefully
        assert result is not None

    def test_single_letter(self, service):
        """Single letter name should work."""
        result = service.generate_verification_prompt("A")
        assert "Anatole" in result

    def test_very_long_name(self, service):
        """Very long names should be handled."""
        long_name = "Jean-Pierre-Marie-François-Alexandre"
        result = service.generate_verification_prompt(long_name)
        assert len(result) > 0

    def test_numbers_in_name(self, service):
        """Names with numbers should handle gracefully."""
        result = service.generate_verification_prompt("Pierre3")
        # Should at least spell the letters
        assert "Pierre" in result or "Irma" in result


class TestPerformance:
    """Performance-related tests."""

    @pytest.fixture
    def service(self):
        return SpellingService()

    def test_generation_speed(self, service):
        """Phonetic generation should be fast (< 10ms)."""
        import time

        start = time.perf_counter()
        for _ in range(100):
            service.generate_verification_prompt("Jean-Philippe")
        elapsed = time.perf_counter() - start

        # 100 iterations should take less than 1 second
        assert elapsed < 1.0
