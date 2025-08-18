from typing import AsyncIterable

from livekit.agents import Agent, ModelSettings
from livekit.agents.voice.transcription.filters import filter_markdown
from livekit.rtc import AudioFrame

AVAILABLE_MOTIVES = [
    "Première consultation d'opthalmologie",
    "Consultation de suivi d'opthalmologie",
    "Renouvellement de lunettes",
    "Essai de lentilles",
    "Bilan lentilles - 1 mois" "Urgence occulaire",
    "Opération Cataracte",
]

SYSTEM_PROMPT = f"""
    You are a friendly medical assistant from the "Clinique Vocca Paris"
    Your goal is to guide the patient through a medical appointment booking.
    
    ## General instructions
    - You are a french-speaking assistant
    - When entering the call, start by greeting the patient, then propose to start the booking workflow.
    
    
    ## Booking workflow
    1. Collect the patient's full name
    2. Collect the patient's birthdate
    3. Ask them their visit motive
    4. Find a suitable availability for the appointment
    5. Book the appointment and thank the patient
"""


class BaseAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(
            instructions=SYSTEM_PROMPT,
            *args,
            **kwargs,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply()

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[AudioFrame]:
        filtered_text = filter_markdown(text)
        return super().tts_node(filtered_text, model_settings)
