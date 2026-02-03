"""
Greeting Agent - Initial patient interaction.

This agent handles the initial greeting and routes based on patient intent.
"""

from livekit.agents import RunContext, function_tool

from src.agents.base import BaseVoccaAgent

# Clinic contact info
CLINIC_PHONE = "01 45 67 89 00"

GREETING_INSTRUCTIONS = f"""
Tu es l'assistant de la Clinique d'ophtalmologie Vocca Paris.

## COMPORTEMENT
- Patient dit oui/d'accord/ok → appelle 'start_booking' SANS RIEN DIRE AVANT
- Patient dit non/autre chose → appelle 'redirect_to_secretariat'
- NE DIS JAMAIS "je m'en occupe", "un instant", ou toute autre phrase avant d'appeler l'outil

## Secrétariat: {CLINIC_PHONE}
"""


class GreetingAgent(BaseVoccaAgent):
    """
    Greeting agent that welcomes patients and routes based on intent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            instructions=GREETING_INSTRUCTIONS,
            *args,
            **kwargs,
        )

    async def on_enter(self) -> None:
        """Greet and ask if they want to book."""
        self.log_agent_action("greeting_patient")
        await self.session.generate_reply(
            instructions="Dis simplement: 'Bonjour et bienvenue à la Clinique d'ophtalmologie Vocca Paris ! Souhaitez-vous prendre un rendez-vous ?'"
        )

    @function_tool()
    async def start_booking(self, context: RunContext) -> tuple:
        """
        Démarre la prise de rendez-vous.
        Utilise cet outil quand le patient dit oui.
        """
        self.log_agent_action("starting_booking")

        from src.agents.identity import IdentityCollectionAgent

        return (
            IdentityCollectionAgent(chat_ctx=self.chat_ctx),
            "Parfait. Quel est votre prénom ?"
        )


    @function_tool()
    async def redirect_to_secretariat(self, context: RunContext) -> str:
        """
        Redirige vers le secrétariat.
        Utilise quand le patient ne veut pas prendre rdv ou a une autre demande.
        """
        self.log_agent_action("redirecting_to_secretariat")

        return (
            f"Je vous invite à contacter notre secrétariat au {CLINIC_PHONE}. "
            "Ils pourront répondre à toutes vos questions. Bonne journée !"
        )
