"""
Booking Confirmation Agent - Finalizes the appointment booking.

This agent handles the final booking confirmation, ensuring all
information is correct before committing the reservation.
"""

from typing import Optional

from livekit.agents import RunContext, function_tool

from src.agents.base import BaseVoccaAgent
from src.models.booking import AvailabilitySlot, BookingResult
from src.services.booking import get_booking_service

BOOKING_INSTRUCTIONS = """
Tu es un assistant médical qui finalise la réservation du rendez-vous.

## Ton rôle
Le récapitulatif a déjà été présenté. Tu attends juste la confirmation.

## Actions possibles
- Si le patient dit "oui", "c'est bon", "je confirme" → utilise 'confirm_booking'
- Si le patient veut changer → utilise 'cancel_and_restart'
- Si le patient a des questions → réponds brièvement

## IMPORTANT
- N'attends PAS une deuxième confirmation après 'confirm_booking'
- 'confirm_booking' vérifie automatiquement que le créneau est toujours disponible
- Si le créneau n'est plus disponible, l'outil retournera un message d'erreur approprié

## Ton style
- Reste concis
- Pas de phrases répétitives
"""


class BookingConfirmationAgent(BaseVoccaAgent):
    """
    Agent that handles the final booking confirmation and completion.
    """

    def __init__(
        self,
        slot: AvailabilitySlot,
        motive: dict,
        *args,
        **kwargs,
    ):
        super().__init__(
            instructions=BOOKING_INSTRUCTIONS,
            *args,
            **kwargs,
        )
        self._slot = slot
        self._motive = motive
        self._booking_service = get_booking_service()
        self._booking_result: Optional[BookingResult] = None

    async def on_enter(self) -> None:
        """Present summary for confirmation."""
        self.log_agent_action("presenting_summary")

        # Access patient info from session
        patient = self.session.userdata.patient_info

        # Simple confirmation
        summary = (
            f"{patient.first_name} {patient.last_name}, "
            f"{self._slot.formatted_time} avec {self._slot.practitioner_name}, "
            f"{self._motive['name']}. Je confirme ?"
        )

        await self.session.generate_reply(instructions=f"Dis: '{summary}'")

    @function_tool()
    async def confirm_booking(self, context: RunContext) -> str:
        """
        Confirme et effectue la réservation.
        Utilise cet outil quand le patient confirme le rendez-vous.
        """
        patient = context.userdata.patient_info

        self.log_agent_action("confirming_booking", {
            "patient": f"{patient.first_name} {patient.last_name}",
            "slot": self._slot.formatted_time,
        })

        try:
            # Perform the booking
            self._booking_result = await self._booking_service.book_appointment(
                slot=self._slot,
                patient_first_name=patient.first_name,
                patient_last_name=patient.last_name,
                patient_birthdate=patient.birthdate.isoformat() if patient.birthdate else "",
                motive_id=self._motive["id"],
            )

            if self._booking_result.success:
                self.log_agent_action("booking_confirmed", {
                    "booking_id": str(self._booking_result.booking_id),
                })

                return (
                    f"C'est confirmé ! Rendez-vous le {self._slot.formatted_time} "
                    f"avec {self._slot.practitioner_name}. Bonne journée !"
                )
            else:
                self.log_agent_action("booking_failed", {
                    "error": self._booking_result.error_code,
                })
                return self._booking_result.message

        except Exception as e:
            self.log_agent_action("booking_error", {"error": str(e)})
            return (
                "Une erreur est survenue lors de la réservation. "
                "Veuillez réessayer ou contacter la clinique directement."
            )

    @function_tool()
    async def cancel_and_restart(self, context: RunContext) -> tuple:
        """
        Annule et recommence la recherche de créneaux.
        Utilise si le patient veut changer de créneau.
        """
        self.log_agent_action("restarting_availability_search")

        from src.agents.availability import AvailabilityAgent

        return (
            AvailabilityAgent(motive=self._motive, chat_ctx=self.chat_ctx),
            "D'accord, je vous propose d'autres créneaux."
        )
