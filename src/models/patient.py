"""
Patient data models.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PatientInfo(BaseModel):
    """
    Patient information collected during the booking process.

    This model holds all patient-related data with validation
    to ensure data quality.
    """

    first_name: Optional[str] = Field(
        default=None,
        description="Patient's first name",
        min_length=1,
        max_length=100,
    )
    last_name: Optional[str] = Field(
        default=None,
        description="Patient's last name",
        min_length=1,
        max_length=100,
    )
    birthdate: Optional[date] = Field(
        default=None,
        description="Patient's date of birth",
    )

    # Spelling verification tracking
    first_name_confirmed: bool = Field(
        default=False,
        description="Whether the first name spelling has been confirmed",
    )
    last_name_confirmed: bool = Field(
        default=False,
        description="Whether the last name spelling has been confirmed",
    )
    birthdate_confirmed: bool = Field(
        default=False,
        description="Whether the birthdate has been confirmed",
    )

    # Phonetic representations for verification
    first_name_phonetic: Optional[str] = Field(
        default=None,
        description="Phonetic spelling of first name for verification",
    )
    last_name_phonetic: Optional[str] = Field(
        default=None,
        description="Phonetic spelling of last name for verification",
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        """Normalize name by stripping whitespace and title-casing."""
        if v is None:
            return None
        # Strip whitespace but preserve internal formatting (hyphens, apostrophes)
        return v.strip()

    @property
    def full_name(self) -> Optional[str]:
        """Get the full name if both parts are available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return None

    @property
    def is_identity_complete(self) -> bool:
        """Check if all identity information is collected and confirmed."""
        return (
            self.first_name is not None
            and self.last_name is not None
            and self.birthdate is not None
            and self.first_name_confirmed
            and self.last_name_confirmed
            and self.birthdate_confirmed
        )

    @property
    def formatted_birthdate(self) -> Optional[str]:
        """Get formatted birthdate for display (French format)."""
        if self.birthdate:
            return self.birthdate.strftime("%d/%m/%Y")
        return None

    def reset_name_confirmation(self, field: str = "both") -> None:
        """Reset name confirmation status when name is updated."""
        if field in ("first", "both"):
            self.first_name_confirmed = False
        if field in ("last", "both"):
            self.last_name_confirmed = False

    model_config = {"validate_assignment": True}
