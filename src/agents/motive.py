"""
Motive Selection Agent - Helps patient choose their visit reason.

This agent guides patients through selecting the appropriate
consultation type from the available options.
"""

from typing import Annotated, Optional

from livekit.agents import RunContext, function_tool
from pydantic import Field

from src.agents.base import BaseVoccaAgent
from src.config import VISIT_MOTIVES, get_motive_by_id


def _format_motives_list() -> str:
    """Format the list of motives for the system prompt."""
    lines = []
    for i, motive in enumerate(VISIT_MOTIVES, 1):
        lines.append(f"{i}. {motive['name']} ({motive['duration_minutes']} min)")
    return "\n".join(lines)


MOTIVE_INSTRUCTIONS = f"""
Tu sélectionnes le motif de consultation.

## Motifs: {_format_motives_list()}

## PROCESSUS
1. Patient nomme un motif précis → appelle 'select_motive'
2. Patient décrit vaguement son besoin → appelle 'suggest_motive'
3. L'outil retourne une phrase → DIS-LA MOT POUR MOT
4. Patient dit oui → appelle 'proceed_to_availability' IMMÉDIATEMENT, SANS RIEN DIRE

## RÈGLES
- NE JAMAIS reconfirmer un motif déjà confirmé
- NE JAMAIS dire "les créneaux sont prêts, voulez-vous..."
- Après "oui" du patient → tool call direct, pas de texte
"""


class MotiveSelectionAgent(BaseVoccaAgent):
    """
    Agent that helps patients select their visit motive.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            instructions=MOTIVE_INSTRUCTIONS,
            *args,
            **kwargs,
        )
        self._selected_motive: Optional[dict] = None

    async def on_enter(self) -> None:
        """Start motive selection."""
        self.log_agent_action("starting_motive_selection")

        # List the main motives so patient knows what's available
        motives_text = ", ".join([m["name"] for m in VISIT_MOTIVES[:4]]) + ", ou autre"
        await self.session.generate_reply(
            instructions=f"Dis: 'Quel est le motif de votre visite ? Par exemple : {motives_text}.'"
        )

    @function_tool()
    async def select_motive(
        self,
        context: RunContext,
        motive_id: Annotated[
            str,
            Field(
                description="L'identifiant du motif choisi",
                enum=[m["id"] for m in VISIT_MOTIVES],
            )
        ],
    ) -> str:
        """
        Sélectionne le motif de visite.

        Args:
            motive_id: L'identifiant du motif (first_consultation, follow_up,
                      glasses_renewal, lens_trial, lens_checkup, emergency, cataract_surgery)
        """
        motive = get_motive_by_id(motive_id)

        if not motive:
            available = ", ".join([m["id"] for m in VISIT_MOTIVES])
            return f"Ce motif n'existe pas. Les motifs disponibles sont : {available}"

        self._selected_motive = motive

        self.log_agent_action("motive_selected", {"motive_id": motive_id, "motive_name": motive["name"]})

        return f"{motive['name']}, {motive['duration_minutes']} minutes. C'est bien ça ?"

    @function_tool()
    async def suggest_motive(
        self,
        context: RunContext,
        description: Annotated[str, Field(description="Description du besoin du patient")],
    ) -> str:
        """
        Suggère un motif basé sur la description du patient.
        Utilise cet outil quand le patient décrit son besoin sans nommer un motif spécifique.

        Args:
            description: Ce que le patient a décrit
        """
        description_lower = description.lower()

        # Simple keyword matching for demonstration
        if any(w in description_lower for w in ["première", "jamais", "nouveau", "première fois"]):
            suggested = get_motive_by_id("first_consultation")
        elif any(w in description_lower for w in ["contrôle", "suivi", "revoir", "retour"]):
            suggested = get_motive_by_id("follow_up")
        elif any(w in description_lower for w in ["lunettes", "renouvellement", "prescription"]):
            suggested = get_motive_by_id("glasses_renewal")
        elif any(w in description_lower for w in ["lentille", "lentilles", "contact"]):
            suggested = get_motive_by_id("lens_trial")
        elif any(w in description_lower for w in ["urgent", "urgence", "douleur", "rouge", "blessure"]):
            suggested = get_motive_by_id("emergency")
        elif any(w in description_lower for w in ["cataracte", "opération", "chirurgie"]):
            suggested = get_motive_by_id("cataract_surgery")
        else:
            suggested = get_motive_by_id("first_consultation")

        self.log_agent_action("motive_suggested", {
            "description": description,
            "suggested": suggested["id"],
        })

        return (
            f"D'après votre description, je vous suggère : '{suggested['name']}'. "
            f"{suggested['description']}. "
            f"Est-ce que cela correspond à votre besoin ?"
        )

    @function_tool()
    async def proceed_to_availability(self, context: RunContext) -> tuple:
        """
        Passe à la recherche de créneaux disponibles.
        Utilise cet outil quand le motif est confirmé.
        """
        if not self._selected_motive:
            return "Veuillez d'abord sélectionner un motif de visite."

        # Store in session
        context.userdata.selected_motive = self._selected_motive

        self.log_agent_action("proceeding_to_availability", {
            "motive_id": self._selected_motive["id"]
        })

        from src.agents.availability import AvailabilityAgent

        return (
            AvailabilityAgent(
                motive=self._selected_motive,
                chat_ctx=self.chat_ctx,
            ),
            "Voici les créneaux disponibles."
        )
