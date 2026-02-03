"""
Vocca Medical Assistant - Main Entry Point.

This module initializes and runs the LiveKit voice agent for
medical appointment booking at Clinique Vocca Paris.
"""

from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from livekit.agents import (
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.agents.voice import AgentSession
from livekit.agents.voice.room_io import RoomInputOptions
from livekit.plugins import azure, noise_cancellation, openai, silero
from livekit.plugins.azure.tts import ProsodyConfig
from loguru import logger

from src.agents.greeting import GreetingAgent
from src.config import get_settings
from userdata import SessionUserData

# Load environment variables
load_dotenv()


def prewarm(proc: JobProcess) -> None:
    """
    Pre-warm resources that can be shared across sessions.

    This function runs once when the worker process starts,
    allowing us to load expensive resources like VAD models.
    """
    logger.info("Warming up agent resources...")

    # Load Silero VAD with optimized settings for telephony
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=0.1,      # Minimum speech duration to trigger
        min_silence_duration=0.8,     # Pause before considering end of speech
        prefix_padding_duration=0.5,   # Audio to keep before speech detection
        max_buffered_speech=15,        # Maximum buffered speech duration
        activation_threshold=0.5,      # Sensitivity threshold
    )

    logger.info("Agent resources warmed up successfully")


async def entrypoint(ctx: JobContext) -> None:
    """
    Main entry point for each voice session.

    This function is called for each new room/call and sets up
    the agent session with all necessary components.
    """
    settings = get_settings()

    # Create unique session identifier for tracking
    call_id = str(uuid4())[:8]
    session_start = datetime.now().isoformat()

    logger.info(f"Starting new session: call_id={call_id}")

    # Initialize session userdata
    userdata = SessionUserData(
        call_id=call_id,
        session_started_at=session_start,
    )

    # Configure the agent session with all components
    session = AgentSession[SessionUserData](
        userdata=userdata,
        # Speech-to-Text: Azure with French language
        stt=azure.STT(
            language=settings.default_language,
        ),
        # Large Language Model: Azure OpenAI GPT-4o
        llm=openai.LLM.with_azure(
            temperature=0,  # Deterministic responses for consistency
        ),
        # Text-to-Speech: Azure with French voice
        # Prosody rate: 'x-slow', 'slow', 'medium', 'fast', 'x-fast'
        tts=azure.TTS(
            voice="fr-FR-DeniseNeural",  # Natural French voice
            prosody=ProsodyConfig(rate="medium"),
        ),
        # Voice Activity Detection: Pre-loaded Silero
        vad=ctx.proc.userdata["vad"],
        # Turn detection mode
        turn_detection="vad",
        # Maximum tool execution steps per turn
        max_tool_steps=5,
    )

    # Set up metrics collection for monitoring
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics_collected(ev):
        """Log metrics for observability."""
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_session_summary():
        """Log session summary on completion."""
        summary = usage_collector.get_summary()
        logger.info(f"Session {call_id} completed. Usage: {summary}")

    ctx.add_shutdown_callback(log_session_summary)

    # Start the session with the Greeting Agent
    await session.start(
        agent=GreetingAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            video_enabled=False,
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    logger.info(f"Session {call_id} started successfully")


def main():
    """Run the agent worker."""
    logger.info("Starting Vocca Medical Assistant Agent")

    cli.run_app(
        WorkerOptions(
            prewarm_fnc=prewarm,
            entrypoint_fnc=entrypoint,
        )
    )


if __name__ == "__main__":
    main()
