"""
Session Userdata model for the Vocca Medical Assistant.

This module defines the session state that persists across
the multi-agent workflow.
"""

from typing import Dict, Optional

from livekit.agents import Agent
from pydantic import BaseModel, Field

from src.models.patient import PatientInfo
from src.models.booking import AvailabilitySlot


class SessionUserData(BaseModel):
    """
    User data that persists across the voice session.
    
    This model holds all state needed during the booking workflow,
    passed between agents through the session context.
    """

    # Patient information collected during identity phase
    patient_info: PatientInfo = Field(
        default_factory=PatientInfo,
        description="Patient identity information",
    )

    # Selected visit motive
    selected_motive: Optional[dict] = Field(
        default=None,
        description="The selected visit motive",
    )

    # Selected availability slot
    selected_slot: Optional[AvailabilitySlot] = Field(
        default=None,
        description="The selected appointment slot",
    )

    # Agent registry for multi-agent workflow
    agents: Dict[str, Agent] = Field(
        default_factory=dict,
        description="Registered agents",
    )

    # Session metadata
    session_started_at: Optional[str] = Field(
        default=None,
        description="Session start timestamp",
    )
    
    call_id: Optional[str] = Field(
        default=None,
        description="Unique call identifier for tracking",
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def is_booking_complete(self) -> bool:
        """Check if all booking information is complete."""
        return (
            self.patient_info.is_identity_complete
            and self.selected_motive is not None
            and self.selected_slot is not None
        )

    def reset(self) -> None:
        """Reset the session state for a new booking."""
        self.patient_info = PatientInfo()
        self.selected_motive = None
        self.selected_slot = None


# Alias for backward compatibility
UserData = SessionUserData
