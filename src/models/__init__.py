"""
Data models for the Vocca Medical Assistant.
"""

from .booking import AvailabilitySlot, BookingResult
from .patient import PatientInfo

__all__ = [
    "PatientInfo",
    "AvailabilitySlot",
    "BookingResult",
]
