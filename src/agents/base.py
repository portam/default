"""
Base Agent class for Vocca Medical Assistant.

All specialized agents inherit from this base class which provides
common functionality and pipeline configurations.
"""

from typing import AsyncIterable, Optional

from livekit.agents import Agent, ModelSettings
from livekit.agents.voice.transcription.filters import filter_markdown
from livekit.rtc import AudioFrame
from loguru import logger

from src.config import get_settings


class BaseVoccaAgent(Agent):
    """
    Base agent class with common configuration and utilities.

    Provides:
    - Standardized TTS node with markdown filtering
    - Common logging utilities
    - Access to settings and services
    """

    def __init__(
        self,
        instructions: str,
        *args,
        **kwargs,
    ):
        super().__init__(
            instructions=instructions,
            *args,
            **kwargs,
        )
        self.settings = get_settings()

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[AudioFrame]:
        """
        Custom TTS node that filters out markdown formatting.

        This ensures clean speech output without pronunciation
        issues from markdown symbols.
        """
        filtered_text = filter_markdown(text)
        return super().tts_node(filtered_text, model_settings)

    def log_agent_action(self, action: str, details: Optional[dict] = None) -> None:
        """Log agent actions for monitoring and debugging."""
        extra = {"agent": self.__class__.__name__, "action": action}
        if details:
            extra.update(details)
        logger.info(f"{self.__class__.__name__}: {action}", extra=extra)
