"""
Booking Service - Logs appointment bookings.

Per the README requirements, this service only logs the booking
action and arguments (no actual external calendar integration required).
"""

from typing import Optional
from uuid import uuid4

from loguru import logger

from src.config import get_motive_by_id
from src.models.booking import AvailabilitySlot, BookingResult
from src.services.availability import get_availability_service


class BookingService:
    """
    Service for logging appointment bookings.

    As per README: "Calendar booking: Should only log the booking
    action and arguments (no actual external calendar integration required)"
    """

    def __init__(self):
        self._availability_service = get_availability_service()

    async def book_appointment(
        self,
        slot: AvailabilitySlot,
        patient_first_name: str,
        patient_last_name: str,
        patient_birthdate: str,
        motive_id: str,
    ) -> BookingResult:
        """
        Book an appointment - verifies slot availability and logs the booking.

        Args:
            slot: The availability slot to book
            patient_first_name: Patient's first name
            patient_last_name: Patient's last name
            patient_birthdate: Patient's birthdate (YYYY-MM-DD format)
            motive_id: Visit motive identifier

        Returns:
            BookingResult with success status
        """
        try:
            # Verify slot is still available
            is_available = await self._availability_service.check_slot_availability(slot.id)
            if not is_available:
                return BookingResult(
                    success=False,
                    message="Ce créneau n'est plus disponible. Voulez-vous choisir un autre horaire ?",
                    error_code="SLOT_UNAVAILABLE",
                )

            # Reserve the slot
            reserved = await self._availability_service.reserve_slot(slot.id)
            if not reserved:
                return BookingResult(
                    success=False,
                    message="Ce créneau vient d'être réservé. Voulez-vous choisir un autre horaire ?",
                    error_code="RESERVATION_CONFLICT",
                )

            # Get motive details
            motive = get_motive_by_id(motive_id)
            motive_name = motive["name"] if motive else "Consultation"

            # Generate booking ID
            booking_id = uuid4()

            # Log the booking (as per README requirement)
            logger.info("=" * 60)
            logger.info("📅 CALENDAR BOOKING LOG")
            logger.info("=" * 60)
            logger.info(f"Booking ID: {booking_id}")
            logger.info(f"Patient: {patient_first_name} {patient_last_name}")
            logger.info(f"Birthdate: {patient_birthdate}")
            logger.info(f"Date/Time: {slot.formatted_time}")
            logger.info(f"Practitioner: {slot.practitioner_name}")
            logger.info(f"Motive: {motive_name}")
            logger.info(f"Duration: {slot.duration_minutes} minutes")
            logger.info("=" * 60)

            return BookingResult(
                success=True,
                booking_id=booking_id,
                message=f"Rendez-vous confirmé pour {slot.formatted_time} avec {slot.practitioner_name}.",
            )

        except Exception as e:
            logger.error(f"Booking error: {e}")
            return BookingResult(
                success=False,
                message="Une erreur est survenue. Veuillez réessayer.",
                error_code="BOOKING_ERROR",
            )


# Singleton instance
_booking_service: Optional[BookingService] = None


def get_booking_service() -> BookingService:
    """Get the singleton booking service instance."""
    global _booking_service
    if _booking_service is None:
        _booking_service = BookingService()
    return _booking_service
