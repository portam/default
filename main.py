from dotenv import load_dotenv
from livekit.agents import (
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import AgentSession
from livekit.agents.voice.room_io import RoomInputOptions
from livekit.plugins import azure, noise_cancellation, openai, silero
from loguru import logger

from agent import BaseAgent
from userdata import UserData

load_dotenv()


def prewarm(proc: JobProcess):
    logger.info("Warming up")
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=0.1,
        min_silence_duration=0.8,
        prefix_padding_duration=0.5,
        max_buffered_speech=15,
        activation_threshold=0.5,
    )


async def entrypoint(ctx: JobContext):
    logger.info("Taking call")

    userdata = UserData()

    session = AgentSession[UserData](
        userdata=userdata,
        stt=azure.STT(language="fr-FR"),
        llm=openai.LLM.with_azure(temperature=0),
        tts=azure.TTS(voice="fr-FR-DeniseNeural"),
        vad=ctx.proc.userdata["vad"],
        turn_detection="vad",
        max_tool_steps=3,
    )

    # Start session
    await session.start(
        agent=BaseAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            video_enabled=False,
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )


if __name__ == "__main__":
    logger.info("Starting agent")
    cli.run_app(
        WorkerOptions(
            prewarm_fnc=prewarm,
            entrypoint_fnc=entrypoint,
        )
    )
