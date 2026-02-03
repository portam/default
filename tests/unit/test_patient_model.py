"""
Unit tests for the Patient model.
"""

from datetime import date

from src.models.patient import PatientInfo


class TestPatientInfo:
    """Test patient information model."""

    def test_default_initialization(self):
        """Default patient should have no data."""
        patient = PatientInfo()
        assert patient.first_name is None
        assert patient.last_name is None
        assert patient.birthdate is None
        assert patient.first_name_confirmed is False
        assert patient.last_name_confirmed is False
        assert patient.birthdate_confirmed is False

    def test_full_initialization(self):
        """Patient with all data should be valid."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=True,
            last_name_confirmed=True,
            birthdate_confirmed=True,
        )
        assert patient.first_name == "Marie"
        assert patient.last_name == "Dupont"
        assert patient.birthdate == date(1990, 5, 15)

    # ==================== Identity Completeness ====================

    def test_identity_complete_all_confirmed(self):
        """Identity is complete when all fields are filled and confirmed."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=True,
            last_name_confirmed=True,
            birthdate_confirmed=True,
        )
        assert patient.is_identity_complete is True

    def test_identity_incomplete_missing_first_name(self):
        """Identity is incomplete without first name."""
        patient = PatientInfo(
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            last_name_confirmed=True,
            birthdate_confirmed=True,
        )
        assert patient.is_identity_complete is False

    def test_identity_incomplete_missing_last_name(self):
        """Identity is incomplete without last name."""
        patient = PatientInfo(
            first_name="Marie",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=True,
            birthdate_confirmed=True,
        )
        assert patient.is_identity_complete is False

    def test_identity_incomplete_missing_birthdate(self):
        """Identity is incomplete without birthdate."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            first_name_confirmed=True,
            last_name_confirmed=True,
        )
        assert patient.is_identity_complete is False

    def test_identity_incomplete_unconfirmed_first_name(self):
        """Identity is incomplete with unconfirmed first name."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=False,  # Not confirmed
            last_name_confirmed=True,
            birthdate_confirmed=True,
        )
        assert patient.is_identity_complete is False

    def test_identity_incomplete_unconfirmed_last_name(self):
        """Identity is incomplete with unconfirmed last name."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=True,
            last_name_confirmed=False,  # Not confirmed
            birthdate_confirmed=True,
        )
        assert patient.is_identity_complete is False

    def test_identity_incomplete_unconfirmed_birthdate(self):
        """Identity is incomplete with unconfirmed birthdate."""
        patient = PatientInfo(
            first_name="Marie",
            last_name="Dupont",
            birthdate=date(1990, 5, 15),
            first_name_confirmed=True,
            last_name_confirmed=True,
            birthdate_confirmed=False,  # Not confirmed
        )
        assert patient.is_identity_complete is False

    # ==================== Formatted Birthdate ====================

    def test_formatted_birthdate_french_format(self):
        """Birthdate should format as DD/MM/YYYY (French format)."""
        patient = PatientInfo(birthdate=date(1990, 5, 15))
        assert patient.formatted_birthdate == "15/05/1990"

    def test_formatted_birthdate_single_digit_day(self):
        """Single digit day should be zero-padded."""
        patient = PatientInfo(birthdate=date(1990, 12, 5))
        assert patient.formatted_birthdate == "05/12/1990"

    def test_formatted_birthdate_single_digit_month(self):
        """Single digit month should be zero-padded."""
        patient = PatientInfo(birthdate=date(1990, 3, 15))
        assert patient.formatted_birthdate == "15/03/1990"

    def test_formatted_birthdate_none(self):
        """None birthdate should return empty string or None."""
        patient = PatientInfo()
        result = patient.formatted_birthdate
        assert result is None or result == ""

    # ==================== Phonetic Representations ====================

    def test_phonetic_first_name(self):
        """Phonetic first name should be storable."""
        patient = PatientInfo(
            first_name="Marie",
            first_name_phonetic="M comme Marcel, A comme Anatole...",
        )
        assert patient.first_name_phonetic is not None

    def test_phonetic_last_name(self):
        """Phonetic last name should be storable."""
        patient = PatientInfo(
            last_name="Dupont",
            last_name_phonetic="D comme Désiré, U comme Ursule...",
        )
        assert patient.last_name_phonetic is not None


class TestPatientInfoEdgeCases:
    """Edge case tests for patient info."""

    def test_hyphenated_name(self):
        """Hyphenated names should be valid."""
        patient = PatientInfo(
            first_name="Jean-Pierre",
            last_name="Martin-Dupont",
        )
        assert patient.first_name == "Jean-Pierre"
        assert patient.last_name == "Martin-Dupont"

    def test_accented_name(self):
        """Accented names should be valid."""
        patient = PatientInfo(
            first_name="Hélène",
            last_name="Bézier",
        )
        assert patient.first_name == "Hélène"
        assert patient.last_name == "Bézier"

    def test_apostrophe_name(self):
        """Names with apostrophes should be valid."""
        patient = PatientInfo(
            first_name="Jean",
            last_name="D'Angelo",
        )
        assert patient.last_name == "D'Angelo"

    def test_ancient_birthdate(self):
        """Very old birthdates should be valid."""
        patient = PatientInfo(birthdate=date(1920, 1, 1))
        assert patient.formatted_birthdate == "01/01/1920"

    def test_recent_birthdate(self):
        """Recent birthdates should be valid."""
        patient = PatientInfo(birthdate=date(2023, 12, 31))
        assert patient.formatted_birthdate == "31/12/2023"
