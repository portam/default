"""
Availability Agent - Finds and presents available appointment slots.

This agent queries the availability service and helps patients
choose a suitable time slot.
"""

from datetime import datetime, timedelta
from typing import Annotated, Dict, List, Optional
from uuid import UUID

from livekit.agents import RunContext, function_tool
from pydantic import Field

from src.agents.base import BaseVoccaAgent
from src.config import FRENCH_DAY_NAME_TO_INDEX, FRENCH_DAY_NAMES
from src.models.booking import AvailabilitySlot
from src.services.availability import get_availability_service

AVAILABILITY_INSTRUCTIONS = """
Tu aides le patient à choisir un créneau.

## PROCESSUS EN 2 ÉTAPES
1. Patient choisit un créneau → appelle un outil de sélection
2. L'outil dit "c'est noté" → appelle 'proceed_to_booking' IMMÉDIATEMENT (sans parler)

## OUTILS DE SÉLECTION
- Numéro ("le 2") → 'select_slot_by_number'
- Heure + médecin ("10h avec Martin") → 'select_slot_by_criteria'

## OUTILS DE RECHERCHE
- Date précise ("le 5 février") → 'search_slots_by_date' avec day=5, month=2
- Jour de semaine ("jeudi") → 'search_slots_by_day'
- Médecin ("avec Dr Dubois") → 'search_slots_by_practitioner'
- Horaire ("après 14h") → 'search_slots_by_time'
- Plus de choix → 'show_other_slots'

## CHANGEMENT DE MOTIF
- "changer pour X" → 'update_motive' (retourne directement les créneaux)

## RÈGLES
- JAMAIS dire "confirmé" - c'est l'agent booking qui confirme
- Après sélection → tool call 'proceed_to_booking' sans rien dire
"""


class AvailabilityAgent(BaseVoccaAgent):
    """
    Agent that handles availability search and slot selection.
    """

    def __init__(self, motive: dict, *args, **kwargs):
        super().__init__(
            instructions=AVAILABILITY_INSTRUCTIONS,
            *args,
            **kwargs,
        )
        self._motive = motive
        self._availability_service = get_availability_service()
        self._available_slots: List[AvailabilitySlot] = []
        self._all_fetched_slots: List[AvailabilitySlot] = []  # All slots fetched so far
        self._shown_slot_ids: set = set()  # Track which slots have been shown
        self._slots_by_id: Dict[UUID, AvailabilitySlot] = {}
        self._selected_slot: Optional[AvailabilitySlot] = None
        self._current_offset: int = 0  # For pagination

    async def on_enter(self) -> None:
        """Search for available slots when entering."""
        self.log_agent_action("searching_availability", {"motive_id": self._motive["id"]})

        # Fetch initial availabilities
        try:
            self._all_fetched_slots = await self._availability_service.get_availabilities(
                motive_id=self._motive["id"],
                limit=20,  # Fetch more to allow pagination
            )
            # Show first 5
            self._available_slots = self._all_fetched_slots[:5]
            self._current_offset = 5
            self._slots_by_id = {slot.id: slot for slot in self._all_fetched_slots}
            # Track shown slots
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)

            if self._available_slots:
                # Say the slots directly, don't ask permission
                slots_text = self._format_slots_for_speech()
                await self.session.generate_reply(
                    instructions=f"Dis exactement: '{slots_text}'"
                )
            else:
                await self.session.generate_reply(
                    instructions="Dis: 'Je n'ai pas trouvé de créneaux dans les deux prochaines semaines. Voulez-vous que je cherche plus loin ?'"
                )
        except Exception as e:
            self.log_agent_action("availability_error", {"error": str(e)})
            await self.session.generate_reply(
                instructions=(
                    "J'ai un problème technique pour accéder aux disponibilités. "
                    "Veuillez patienter un instant pendant que je réessaie."
                )
            )

    def _format_slots_for_speech(self) -> str:
        """Format available slots for natural speech."""
        if not self._available_slots:
            return "Je n'ai pas trouvé de créneaux disponibles."

        slot_descriptions = []
        for i, slot in enumerate(self._available_slots[:5], 1):
            slot_descriptions.append(f"{i}. {slot.formatted_time} avec {slot.practitioner_name}")

        # Use line breaks for clarity
        slots_text = ". ".join(slot_descriptions)

        return (
            f"Voici {len(self._available_slots)} créneaux : {slots_text}. "
            f"Lequel préférez-vous ?"
        )

    @function_tool()
    async def show_other_slots(
        self,
        context: RunContext,
    ) -> str:
        """
        Montre d'autres créneaux disponibles (différents de ceux déjà présentés).
        Utilise cette fonction quand le patient dit 'autres créneaux', 'autres disponibilités', etc.
        """
        # Get next batch from already fetched slots
        remaining_slots = [
            slot for slot in self._all_fetched_slots
            if slot.id not in self._shown_slot_ids
        ]

        if remaining_slots:
            # Show next 5 unshown slots
            self._available_slots = remaining_slots[:5]
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)
            self._current_offset += 5

            self.log_agent_action("show_other_slots", {
                "slots_shown": len(self._available_slots),
                "remaining": len(remaining_slots) - len(self._available_slots),
            })

            return self._format_slots_for_speech()
        else:
            # Need to fetch more from API with offset
            try:
                new_slots = await self._availability_service.get_availabilities(
                    motive_id=self._motive["id"],
                    limit=20,
                    offset=len(self._all_fetched_slots),
                )

                if new_slots:
                    self._all_fetched_slots.extend(new_slots)
                    self._slots_by_id.update({slot.id: slot for slot in new_slots})
                    self._available_slots = new_slots[:5]
                    for slot in self._available_slots:
                        self._shown_slot_ids.add(slot.id)

                    return self._format_slots_for_speech()
                else:
                    return "Je n'ai plus d'autres créneaux disponibles pour cette période. Souhaitez-vous que je cherche sur une période plus longue ?"

            except Exception as e:
                self.log_agent_action("fetch_error", {"error": str(e)})
                return "J'ai eu un problème technique. Pouvez-vous réessayer ?"

    @function_tool()
    async def search_more_slots(
        self,
        context: RunContext,
        weeks_ahead: Annotated[int, Field(description="Nombre de semaines à chercher", ge=1, le=8)] = 4,
    ) -> str:
        """
        Recherche plus de créneaux sur une période plus longue.

        Args:
            weeks_ahead: Nombre de semaines à l'avance (1-8)
        """
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(weeks=weeks_ahead)

            new_slots = await self._availability_service.get_availabilities(
                motive_id=self._motive["id"],
                start_date=start_date,
                end_date=end_date,
                limit=20,
            )

            # Filter out already shown slots
            unseen_slots = [s for s in new_slots if s.id not in self._shown_slot_ids]
            self._all_fetched_slots.extend(unseen_slots)
            self._slots_by_id.update({slot.id: slot for slot in unseen_slots})

            self._available_slots = unseen_slots[:5]
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)

            self.log_agent_action("extended_search", {
                "weeks_ahead": weeks_ahead,
                "slots_found": len(unseen_slots),
            })

            if self._available_slots:
                return self._format_slots_for_speech()
            else:
                return "Je n'ai pas trouvé de nouveaux créneaux sur cette période."

        except Exception as e:
            self.log_agent_action("search_error", {"error": str(e)})
            return "J'ai eu un problème technique. Pouvez-vous réessayer ?"

    @function_tool()
    async def search_slots_by_date(
        self,
        context: RunContext,
        day: Annotated[int, Field(description="Le jour du mois (1-31)", ge=1, le=31)],
        month: Annotated[int, Field(description="Le mois (1-12)", ge=1, le=12)],
    ) -> str:
        """
        Recherche des créneaux pour une date précise.
        Utilise quand le patient demande une date (ex: "le 5 février", "le 10 mars").

        Args:
            day: Le jour du mois
            month: Le numéro du mois (1=janvier, 2=février, etc.)
        """
        try:
            # Build target date
            year = datetime.now().year
            target_date = datetime(year, month, day)
            
            # If date is in the past, use next year
            if target_date < datetime.now():
                target_date = datetime(year + 1, month, day)
            
            # Check if weekend
            if target_date.weekday() >= 5:
                return f"Le {day}/{month} est un {FRENCH_DAY_NAMES[target_date.weekday()].lower()}, nous ne sommes pas ouverts. Voulez-vous le jour précédent ou suivant ?"

            # Fetch slots for that specific day
            start = target_date.replace(hour=0, minute=0, second=0)
            end = target_date.replace(hour=23, minute=59, second=59)
            
            new_slots = await self._availability_service.get_availabilities(
                motive_id=self._motive["id"],
                start_date=start,
                end_date=end,
                limit=20,
            )
            
            if new_slots:
                self._all_fetched_slots.extend([s for s in new_slots if s.id not in self._slots_by_id])
                self._slots_by_id.update({s.id: s for s in new_slots})
                self._available_slots = new_slots[:5]
                for slot in self._available_slots:
                    self._shown_slot_ids.add(slot.id)
                
                self.log_agent_action("search_by_date", {"date": f"{day}/{month}", "found": len(new_slots)})
                return self._format_slots_for_speech()
            else:
                return f"Je n'ai pas trouvé de créneaux le {day}/{month}. Voulez-vous essayer un autre jour ?"
                
        except ValueError:
            return f"La date {day}/{month} n'est pas valide. Pouvez-vous préciser une autre date ?"
        except Exception as e:
            self.log_agent_action("search_error", {"error": str(e)})
            return "Erreur lors de la recherche. Veuillez réessayer."

    @function_tool()
    async def search_slots_by_day(
        self,
        context: RunContext,
        day_name: Annotated[str, Field(description="Nom du jour en français: lundi, mardi, mercredi, jeudi, vendredi, samedi")],
    ) -> str:
        """
        Recherche des créneaux pour un jour spécifique de la semaine.
        Utilise quand le patient demande un jour précis (ex: "plutôt jeudi", "un autre jour").

        Args:
            day_name: Le nom du jour souhaité (lundi, mardi, etc.)
        """
        target_day = FRENCH_DAY_NAME_TO_INDEX.get(day_name.lower())

        if target_day is None:
            return f"Je n'ai pas compris le jour '{day_name}'. Pouvez-vous préciser ?"

        # Filter from all fetched slots or fetch new ones
        matching_slots = [
            slot for slot in self._all_fetched_slots
            if slot.start_time.weekday() == target_day and slot.id not in self._shown_slot_ids
        ]

        if not matching_slots:
            # Fetch more slots over 4 weeks
            try:
                new_slots = await self._availability_service.get_availabilities(
                    motive_id=self._motive["id"],
                    start_date=datetime.now(),
                    end_date=datetime.now() + timedelta(weeks=4),
                    limit=20,
                )
                matching_slots = [
                    s for s in new_slots
                    if s.start_time.weekday() == target_day and s.id not in self._shown_slot_ids
                ]
                self._all_fetched_slots.extend([s for s in new_slots if s.id not in self._slots_by_id])
                self._slots_by_id.update({s.id: s for s in new_slots})
            except Exception:
                return "Erreur lors de la recherche. Veuillez réessayer."

        if matching_slots:
            self._available_slots = matching_slots[:5]
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)
            self.log_agent_action("search_by_day", {"day": day_name, "found": len(matching_slots)})
            return self._format_slots_for_speech()
        else:
            return f"Je n'ai pas trouvé de créneaux disponibles le {day_name}. Voulez-vous un autre jour ?"

    @function_tool()
    async def search_slots_by_practitioner(
        self,
        context: RunContext,
        practitioner_name: Annotated[str, Field(description="Nom du praticien souhaité")],
    ) -> str:
        """
        Recherche des créneaux avec un praticien spécifique.
        Utilise quand le patient demande un médecin précis (ex: "avec Dr Martin").

        Args:
            practitioner_name: Le nom du praticien
        """
        # Filter from all fetched slots
        name_lower = practitioner_name.lower()
        matching_slots = [
            slot for slot in self._all_fetched_slots
            if name_lower in slot.practitioner_name.lower() and slot.id not in self._shown_slot_ids
        ]

        if not matching_slots:
            # Fetch more slots
            try:
                new_slots = await self._availability_service.get_availabilities(
                    motive_id=self._motive["id"],
                    start_date=datetime.now(),
                    end_date=datetime.now() + timedelta(weeks=4),
                    limit=20,
                )
                matching_slots = [
                    s for s in new_slots
                    if name_lower in s.practitioner_name.lower() and s.id not in self._shown_slot_ids
                ]
                self._all_fetched_slots.extend([s for s in new_slots if s.id not in self._slots_by_id])
                self._slots_by_id.update({s.id: s for s in new_slots})
            except Exception:
                return "Erreur lors de la recherche. Veuillez réessayer."

        if matching_slots:
            self._available_slots = matching_slots[:5]
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)
            self.log_agent_action("search_by_practitioner", {"name": practitioner_name, "found": len(matching_slots)})
            return self._format_slots_for_speech()
        else:
            return f"Je n'ai pas trouvé de créneaux avec {practitioner_name}. Voulez-vous voir les autres praticiens ?"

    @function_tool()
    async def search_slots_by_time(
        self,
        context: RunContext,
        after_hour: Annotated[Optional[int], Field(description="Heure minimum (ex: 14 pour après 14h)", ge=8, le=19)] = None,
        before_hour: Annotated[Optional[int], Field(description="Heure maximum (ex: 12 pour le matin)", ge=9, le=20)] = None,
    ) -> str:
        """
        Recherche des créneaux dans une plage horaire.
        Utilise quand le patient demande une heure spécifique (ex: "après 14h", "le matin", "avant midi").

        Args:
            after_hour: Heure après laquelle chercher (8-19)
            before_hour: Heure avant laquelle chercher (9-20)
        """
        def matches_time(slot: AvailabilitySlot) -> bool:
            hour = slot.start_time.hour
            if after_hour and hour < after_hour:
                return False
            if before_hour and hour >= before_hour:
                return False
            return True

        matching_slots = [
            slot for slot in self._all_fetched_slots
            if matches_time(slot) and slot.id not in self._shown_slot_ids
        ]

        if not matching_slots:
            # Fetch more slots
            try:
                new_slots = await self._availability_service.get_availabilities(
                    motive_id=self._motive["id"],
                    start_date=datetime.now(),
                    end_date=datetime.now() + timedelta(weeks=4),
                    limit=20,
                )
                matching_slots = [
                    s for s in new_slots if matches_time(s) and s.id not in self._shown_slot_ids
                ]
                self._all_fetched_slots.extend([s for s in new_slots if s.id not in self._slots_by_id])
                self._slots_by_id.update({s.id: s for s in new_slots})
            except Exception:
                return "Erreur lors de la recherche. Veuillez réessayer."

        if matching_slots:
            self._available_slots = matching_slots[:5]
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)
            time_desc = ""
            if after_hour:
                time_desc = f"après {after_hour}h"
            if before_hour:
                time_desc = f"avant {before_hour}h" if not time_desc else f"{time_desc} et avant {before_hour}h"
            self.log_agent_action("search_by_time", {"after": after_hour, "before": before_hour, "found": len(matching_slots)})
            return self._format_slots_for_speech()
        else:
            time_desc = ""
            if after_hour:
                time_desc = f"après {after_hour}h"
            if before_hour:
                time_desc = f"avant {before_hour}h" if not time_desc else f"{time_desc} et avant {before_hour}h"
            return f"Je n'ai pas trouvé de créneaux {time_desc}. Voulez-vous une autre plage horaire ?"

    @function_tool()
    async def select_slot_by_number(
        self,
        context: RunContext,
        slot_number: Annotated[int, Field(description="Le numéro du créneau choisi", ge=1, le=10)],
    ) -> str:
        """
        Sélectionne un créneau par son numéro dans la liste.

        Args:
            slot_number: Le numéro du créneau (1 pour le premier, etc.)
        """
        if slot_number < 1 or slot_number > len(self._available_slots):
            return f"Ce numéro n'est pas valide. Choisissez un numéro entre 1 et {len(self._available_slots)}."

        self._selected_slot = self._available_slots[slot_number - 1]

        self.log_agent_action("slot_selected", {
            "slot_id": str(self._selected_slot.id),
            "time": self._selected_slot.formatted_time,
        })

        # Don't say "confirmé" - just acknowledge selection. Booking agent confirms.
        return f"{self._selected_slot.formatted_time} avec {self._selected_slot.practitioner_name}, c'est noté."

    @function_tool()
    async def select_slot_by_criteria(
        self,
        context: RunContext,
        hour: Annotated[Optional[int], Field(description="L'heure souhaitée (ex: 10 pour 10h)")] = None,
        minute: Annotated[Optional[int], Field(description="Les minutes (ex: 30 pour 10h30)")] = None,
        practitioner_name: Annotated[Optional[str], Field(description="Le nom du praticien (ex: Martin, Dubois)")] = None,
    ) -> str:
        """
        Sélectionne un créneau par heure et/ou praticien.
        Utilise cet outil quand le patient dit une heure précise ou un nom de médecin.

        Args:
            hour: L'heure souhaitée (9-18)
            minute: Les minutes (0 ou 30 généralement)
            practitioner_name: Nom du praticien (partiel accepté)
        """
        matching_slots = self._available_slots.copy()

        # Filter by hour
        if hour is not None:
            matching_slots = [s for s in matching_slots if s.start_time.hour == hour]
            if minute is not None:
                matching_slots = [s for s in matching_slots if s.start_time.minute == minute]

        # Filter by practitioner name
        if practitioner_name:
            name_lower = practitioner_name.lower()
            matching_slots = [
                s for s in matching_slots
                if name_lower in s.practitioner_name.lower()
            ]

        if not matching_slots:
            return "Je n'ai pas trouvé de créneau correspondant. Pouvez-vous préciser ou choisir un numéro dans la liste ?"

        # Take the first matching slot
        self._selected_slot = matching_slots[0]

        self.log_agent_action("slot_selected_by_criteria", {
            "slot_id": str(self._selected_slot.id),
            "time": self._selected_slot.formatted_time,
        })

        # Don't say "confirmé" - just acknowledge selection. Booking agent confirms.
        return f"{self._selected_slot.formatted_time} avec {self._selected_slot.practitioner_name}, c'est noté."

    @function_tool()
    async def proceed_to_booking(self, context: RunContext) -> tuple:
        """
        Finalise la réservation du créneau sélectionné.
        Utilise cet outil quand le patient a confirmé son choix de créneau.
        """
        if not self._selected_slot:
            return "Veuillez d'abord sélectionner un créneau."

        # Store in session
        context.userdata.selected_slot = self._selected_slot

        self.log_agent_action("proceeding_to_booking", {
            "slot_id": str(self._selected_slot.id),
        })

        from src.agents.booking import BookingConfirmationAgent

        # Short transition - BookingAgent's on_enter presents the summary
        return (
            BookingConfirmationAgent(
                slot=self._selected_slot,
                motive=self._motive,
                chat_ctx=self.chat_ctx,
            ),
            ""  # on_enter will present the summary
        )

    @function_tool()
    async def update_motive(
        self,
        context: RunContext,
        new_motive_id: Annotated[
            str,
            Field(
                description="L'identifiant du nouveau motif",
                enum=["first_consultation", "follow_up", "glasses_renewal", "lens_trial", "lens_checkup", "emergency", "cataract_surgery"],
            )
        ],
    ) -> str:
        """
        Change le motif de consultation et recherche de nouveaux créneaux.
        Utilise cet outil quand le patient veut changer le type de consultation.

        Args:
            new_motive_id: L'identifiant du nouveau motif
        """
        from src.config import get_motive_by_id
        
        new_motive = get_motive_by_id(new_motive_id)
        if not new_motive:
            return "Ce motif n'existe pas. Veuillez préciser le type de consultation souhaité."

        self._motive = new_motive
        self.log_agent_action("motive_updated", {"new_motive_id": new_motive_id})

        # Re-fetch slots for the new motive
        try:
            self._all_fetched_slots = await self._availability_service.get_availabilities(
                motive_id=new_motive_id,
                limit=20,
            )
            self._available_slots = self._all_fetched_slots[:5]
            self._current_offset = 5
            self._slots_by_id = {slot.id: slot for slot in self._all_fetched_slots}
            self._shown_slot_ids = set()
            for slot in self._available_slots:
                self._shown_slot_ids.add(slot.id)
            self._selected_slot = None

            if self._available_slots:
                slots_text = self._format_slots_for_speech()
                return f"Motif changé pour {new_motive['name']}. {slots_text}"
            else:
                return f"Motif changé pour {new_motive['name']}. Aucun créneau disponible."
        except Exception as e:
            self.log_agent_action("motive_update_error", {"error": str(e)})
            return "Erreur lors de la recherche des créneaux. Veuillez réessayer."
