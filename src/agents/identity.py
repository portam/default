"""
Identity Collection Agent - Collects and verifies patient identity.

This agent handles the critical task of collecting patient names
and birthdate with careful attention to spelling verification.
"""

from datetime import date
from typing import Annotated, Optional

from livekit.agents import RunContext, function_tool
from pydantic import Field

from src.agents.base import BaseVoccaAgent
from src.config import FRENCH_MONTH_NAMES
from src.services.spelling import get_spelling_service

IDENTITY_INSTRUCTIONS = """
Tu collectes les informations d'identité du patient.

## PROCESSUS
1. Patient donne prénom → 'record_first_name' → DIS MOT POUR MOT ce que l'outil retourne
2. Patient dit oui → 'confirm_first_name' is_correct=true → dis "Quel est votre nom de famille ?"
3. Patient donne nom → 'record_last_name' → DIS MOT POUR MOT ce que l'outil retourne
4. Patient dit oui → 'confirm_last_name' is_correct=true → dis "Quelle est votre date de naissance ?"
5. Patient donne date → 'record_birthdate' → DIS MOT POUR MOT ce que l'outil retourne
6. Patient dit oui → 'proceed_to_motive' IMMÉDIATEMENT

## CRITIQUE
- Quand un outil retourne du texte, TU DOIS LE LIRE TEL QUEL au patient
- NE DIS JAMAIS "Est-ce correct ?" sans avoir d'abord lu l'épellation
- AUCUNE phrase de transition ("parfait", "je vais maintenant", "merci")
"""


class IdentityCollectionAgent(BaseVoccaAgent):
    """
    Agent specialized in collecting and verifying patient identity information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            instructions=IDENTITY_INSTRUCTIONS,
            *args,
            **kwargs,
        )
        self._spelling_service = get_spelling_service()

        # Track collected information
        self._first_name: Optional[str] = None
        self._first_name_confirmed: bool = False
        self._last_name: Optional[str] = None
        self._last_name_confirmed: bool = False
        self._birthdate: Optional[date] = None

    async def on_enter(self) -> None:
        """Identity collection starts - first name was already asked in handoff."""
        self.log_agent_action("starting_identity_collection")
        # The handoff message already asked for the first name, so we just wait for response

    @function_tool()
    async def record_first_name(
        self,
        context: RunContext,
        first_name: Annotated[str, Field(description="Le prénom du patient")],
    ) -> str:
        """
        Enregistre le prénom du patient.
        Utilise cet outil dès que le patient donne son prénom.

        Args:
            first_name: Le prénom tel que compris
        """
        # Check for known misspellings (e.g., "Philip" -> "Philippe")
        correct_spelling = self._spelling_service.find_correct_spelling(first_name)
        if correct_spelling:
            self._first_name = correct_spelling
            self._first_name_confirmed = False
            self.log_agent_action("first_name_corrected", {
                "original": first_name,
                "corrected": correct_spelling
            })
            return self._spelling_service.generate_verification_prompt(correct_spelling)

        self._first_name = first_name
        self._first_name_confirmed = False

        self.log_agent_action("first_name_recorded", {"first_name": first_name})

        # Generate verification prompt with emphasis on potential issues
        return self._spelling_service.generate_verification_prompt(first_name)

    @function_tool()
    async def confirm_first_name(
        self,
        context: RunContext,
        is_correct: Annotated[bool, Field(description="Si l'orthographe est confirmée correcte")],
        corrected_name: Annotated[Optional[str], Field(description="Le prénom corrigé si différent")] = None,
    ) -> str:
        """
        Confirme ou corrige le prénom du patient.

        Args:
            is_correct: True si l'orthographe est correcte
            corrected_name: Le prénom corrigé si l'orthographe était incorrecte
        """
        if is_correct:
            self._first_name_confirmed = True
            self.log_agent_action("first_name_confirmed", {"first_name": self._first_name})

            if self._last_name and self._last_name_confirmed:
                return "Quelle est votre date de naissance ?"
            return "Quel est votre nom de famille ?"

        if corrected_name:
            self._first_name = corrected_name
            # Need to verify the corrected name again
            return await self.record_first_name(context, corrected_name)

        # Suggest alternatives based on phonetic confusions
        if self._first_name:
            alternatives = self._spelling_service.get_possible_confusions(self._first_name)
            if alternatives:
                suggestions = ", ".join(alternatives[:3])
                self._first_name = None
                return f"Peut-être {suggestions} ? Ou pouvez-vous épeler votre prénom ?"

        self._first_name = None
        return "D'accord, pouvez-vous épeler votre prénom lettre par lettre ?"

    @function_tool()
    async def record_last_name(
        self,
        context: RunContext,
        last_name: Annotated[str, Field(description="Le nom de famille du patient")],
    ) -> str:
        """
        Enregistre le nom de famille du patient.

        Args:
            last_name: Le nom de famille tel que compris
        """
        # Check for known misspellings (e.g., "Nuen" -> "Nguyen", "Lefevre" -> "Lefebvre")
        correct_spelling = self._spelling_service.find_correct_spelling(last_name)
        if correct_spelling:
            self._last_name = correct_spelling
            self._last_name_confirmed = False
            self.log_agent_action("last_name_corrected", {
                "original": last_name,
                "corrected": correct_spelling
            })
            return self._spelling_service.generate_verification_prompt(correct_spelling)

        self._last_name = last_name
        self._last_name_confirmed = False

        self.log_agent_action("last_name_recorded", {"last_name": last_name})

        # Generate verification prompt with emphasis on potential issues
        return self._spelling_service.generate_verification_prompt(last_name)

    @function_tool()
    async def confirm_last_name(
        self,
        context: RunContext,
        is_correct: Annotated[bool, Field(description="Si l'orthographe est confirmée correcte")],
        corrected_name: Annotated[Optional[str], Field(description="Le nom corrigé si différent")] = None,
    ) -> str:
        """
        Confirme ou corrige le nom de famille du patient.

        Args:
            is_correct: True si l'orthographe est correcte
            corrected_name: Le nom corrigé si l'orthographe était incorrecte
        """
        if is_correct:
            self._last_name_confirmed = True
            self.log_agent_action("last_name_confirmed", {"last_name": self._last_name})

            if self._birthdate:
                return "Toutes vos informations sont enregistrées."
            return "Quelle est votre date de naissance ?"

        if corrected_name:
            self._last_name = corrected_name
            return await self.record_last_name(context, corrected_name)

        # Suggest alternatives based on phonetic confusions
        if self._last_name:
            alternatives = self._spelling_service.get_possible_confusions(self._last_name)
            if alternatives:
                suggestions = ", ".join(alternatives[:3])
                self._last_name = None
                return f"Peut-être {suggestions} ? Ou pouvez-vous épeler votre nom ?"

        self._last_name = None
        return "D'accord, pouvez-vous épeler votre nom lettre par lettre ?"

    @function_tool()
    async def record_birthdate(
        self,
        context: RunContext,
        day: Annotated[int, Field(description="Le jour de naissance (1-31)", ge=1, le=31)],
        month: Annotated[int, Field(description="Le mois de naissance (1-12)", ge=1, le=12)],
        year: Annotated[int, Field(description="L'année de naissance (format AAAA)", ge=1900, le=2025)],
    ) -> str:
        """
        Enregistre la date de naissance du patient.
        Si le patient confirme ensuite (dit "oui"), utilise IMMEDIATEMENT 'proceed_to_motive'.

        Args:
            day: Jour de naissance (1-31)
            month: Mois de naissance (1-12)
            year: Année de naissance (4 chiffres)
        """
        try:
            self._birthdate = date(year, month, day)

            # Validate it's not in the future
            if self._birthdate > date.today():
                return "Cette date est dans le futur. Pouvez-vous me redonner votre date de naissance ?"

            # Format in French
            formatted = f"{day} {FRENCH_MONTH_NAMES[month]} {year}"

            self.log_agent_action("birthdate_recorded", {"birthdate": str(self._birthdate)})

            return f"{formatted}, c'est correct ?"

        except ValueError:
            return "Cette date n'est pas valide. Pouvez-vous me redonner votre date de naissance ?"

    @function_tool()
    async def proceed_to_motive(self, context: RunContext) -> tuple:
        """
        Passe à la sélection du motif de visite.
        Utilise cet outil IMMEDIATEMENT quand le patient confirme sa date de naissance.
        """
        if not self._first_name_confirmed:
            return "Je dois d'abord confirmer votre prénom."
        if not self._last_name_confirmed:
            return "Je dois d'abord confirmer votre nom de famille."
        if not self._birthdate:
            return "Je dois d'abord enregistrer votre date de naissance."

        self.log_agent_action("identity_complete", {
            "first_name": self._first_name,
            "last_name": self._last_name,
            "birthdate": str(self._birthdate),
        })

        # Store in session userdata
        context.userdata.patient_info.first_name = self._first_name
        context.userdata.patient_info.last_name = self._last_name
        context.userdata.patient_info.birthdate = self._birthdate
        context.userdata.patient_info.first_name_confirmed = True
        context.userdata.patient_info.last_name_confirmed = True

        from src.agents.motive import MotiveSelectionAgent

        # Short transition - MotiveAgent's on_enter handles the rest
        return (
            MotiveSelectionAgent(chat_ctx=self.chat_ctx),
            "Merci."
        )
