"""
Booking-related data models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config import FRENCH_DAY_NAMES, FRENCH_MONTH_NAMES


class AvailabilitySlot(BaseModel):
    """
    Represents an available time slot for booking.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique slot identifier")
    start_time: datetime = Field(description="Start time of the slot")
    end_time: datetime = Field(description="End time of the slot")
    practitioner_name: str = Field(description="Name of the practitioner")
    practitioner_id: str = Field(description="Practitioner identifier")
    motive_id: str = Field(description="Visit motive this slot is for")
    is_available: bool = Field(default=True, description="Whether slot is still available")

    @property
    def duration_minutes(self) -> int:
        """Calculate duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    @property
    def formatted_time(self) -> str:
        """Get human-readable time format (French)."""
        day_name = FRENCH_DAY_NAMES[self.start_time.weekday()]
        month_name = FRENCH_MONTH_NAMES[self.start_time.month]
        return (
            f"{day_name} {self.start_time.day} {month_name} "
            f"à {self.start_time.strftime('%H:%M')}"
        )

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    }


class BookingResult(BaseModel):
    """
    Result of a booking attempt.
    """

    success: bool = Field(description="Whether booking was successful")
    booking_id: Optional[UUID] = Field(default=None, description="Booking confirmation ID")
    message: str = Field(description="Human-readable result message")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
