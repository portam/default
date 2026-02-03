"""
Configuration management for the Vocca Medical Assistant.

This module provides centralized configuration using Pydantic settings
for type-safe environment variable management.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LiveKit Configuration
    livekit_url: str = Field(..., alias="LIVEKIT_URL")
    livekit_api_key: str = Field(..., alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., alias="LIVEKIT_API_SECRET")

    # Azure Configuration
    azure_speech_key: str = Field(..., alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="westeurope", alias="AZURE_SPEECH_REGION")

    # OpenAI Configuration
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(
        default="gpt-4o", alias="AZURE_OPENAI_DEPLOYMENT"
    )

    # Availability API Configuration
    availability_api_url: str = Field(
        default="http://localhost:8080", alias="AVAILABILITY_API_URL"
    )
    availability_api_timeout: int = Field(default=10, alias="AVAILABILITY_API_TIMEOUT")

    # Application Configuration
    clinic_name: str = Field(default="Clinique d'ophtalmologie Vocca Paris", alias="CLINIC_NAME")
    default_language: str = Field(default="fr-FR", alias="DEFAULT_LANGUAGE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Concurrency Settings
    max_concurrent_bookings: int = Field(default=100, alias="MAX_CONCURRENT_BOOKINGS")
    connection_pool_size: int = Field(default=50, alias="CONNECTION_POOL_SIZE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once,
    improving performance for repeated access.
    """
    return Settings()


# Available visit motives - centralized configuration
VISIT_MOTIVES: List[dict] = [
    {
        "id": "first_consultation",
        "name": "Première consultation d'ophtalmologie",
        "duration_minutes": 45,
        "description": "Première visite pour examen complet de la vue",
    },
    {
        "id": "follow_up",
        "name": "Consultation de suivi d'ophtalmologie",
        "duration_minutes": 30,
        "description": "Visite de contrôle après traitement",
    },
    {
        "id": "glasses_renewal",
        "name": "Renouvellement de lunettes",
        "duration_minutes": 20,
        "description": "Examen pour renouvellement de prescription",
    },
    {
        "id": "lens_trial",
        "name": "Essai de lentilles",
        "duration_minutes": 30,
        "description": "Premier essai d'adaptation aux lentilles",
    },
    {
        "id": "lens_checkup",
        "name": "Bilan lentilles - 1 mois",
        "duration_minutes": 20,
        "description": "Contrôle après un mois de port de lentilles",
    },
    {
        "id": "emergency",
        "name": "Urgence oculaire",
        "duration_minutes": 30,
        "description": "Consultation d'urgence pour problème oculaire",
    },
    {
        "id": "cataract_surgery",
        "name": "Opération Cataracte",
        "duration_minutes": 60,
        "description": "Consultation pré-opératoire pour cataracte",
    },
]


# French date formatting constants (centralized to avoid duplication)
FRENCH_DAY_NAMES = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

FRENCH_MONTH_NAMES = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

# Reverse lookup: French day name -> weekday index
FRENCH_DAY_NAME_TO_INDEX = {name.lower(): idx for idx, name in FRENCH_DAY_NAMES.items()}


def get_motive_by_id(motive_id: str) -> dict | None:
    """Get a visit motive by its ID."""
    for motive in VISIT_MOTIVES:
        if motive["id"] == motive_id:
            return motive
    return None


def get_motive_names() -> List[str]:
    """Get list of all motive names for display."""
    return [motive["name"] for motive in VISIT_MOTIVES]
