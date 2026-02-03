"""
Agents module for the Vocca Medical Assistant.

This module implements a multi-agent workflow for handling
medical appointment bookings with specialized agents for each step.
"""

from .availability import AvailabilityAgent
from .base import BaseVoccaAgent
from .booking import BookingConfirmationAgent
from .greeting import GreetingAgent
from .identity import IdentityCollectionAgent
from .motive import MotiveSelectionAgent

__all__ = [
    "BaseVoccaAgent",
    "GreetingAgent",
    "IdentityCollectionAgent",
    "MotiveSelectionAgent",
    "AvailabilityAgent",
    "BookingConfirmationAgent",
]
