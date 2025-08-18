from typing import Dict

from livekit.agents import Agent
from pydantic import BaseModel, Field


class UserData(BaseModel):
    agents: Dict[str, Agent] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
