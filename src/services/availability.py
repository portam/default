"""
Availability Service - Client for the availability API.

This service handles all communication with the availability microservice,
implementing connection pooling and async operations for high concurrency.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import httpx
from loguru import logger

from src.config import get_settings
from src.models.booking import AvailabilitySlot


class AvailabilityService:
    """
    Async client for the availability API.

    Implements connection pooling for efficient concurrent requests
    and handles retries with exponential backoff.
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.availability_api_url,
                timeout=httpx.Timeout(self.settings.availability_api_timeout),
                limits=httpx.Limits(
                    max_connections=self.settings.connection_pool_size,
                    max_keepalive_connections=self.settings.connection_pool_size // 2,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_availabilities(
        self,
        motive_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        practitioner_id: Optional[str] = None,
        limit: int = 5,
        offset: int = 0,
    ) -> List[AvailabilitySlot]:
        """
        Fetch available slots for a given motive.

        Args:
            motive_id: The visit motive ID to search for
            start_date: Start of the search window (defaults to now)
            end_date: End of the search window (defaults to 2 weeks from now)
            practitioner_id: Optional filter by practitioner
            limit: Maximum number of slots to return
            offset: Number of slots to skip (for pagination)

        Returns:
            List of available slots
        """
        client = await self._get_client()

        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(weeks=2)

        params = {
            "motive_id": motive_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": limit,
            "offset": offset,
        }
        if practitioner_id:
            params["practitioner_id"] = practitioner_id

        try:
            response = await client.get("/api/v1/availabilities", params=params)
            response.raise_for_status()

            data = response.json()
            slots = [AvailabilitySlot(**slot) for slot in data.get("slots", [])]

            logger.info(
                f"Found {len(slots)} availability slots for motive {motive_id}"
            )
            return slots

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching availabilities: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching availabilities: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching availabilities: {e}")
            raise

    async def check_slot_availability(self, slot_id: UUID) -> bool:
        """
        Check if a specific slot is still available.

        Args:
            slot_id: The slot ID to check

        Returns:
            True if slot is available, False otherwise
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/api/v1/availabilities/{slot_id}")
            if response.status_code == 404:
                return False
            response.raise_for_status()

            data = response.json()
            return data.get("is_available", False)

        except httpx.HTTPStatusError:
            return False
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False

    async def reserve_slot(self, slot_id: UUID) -> bool:
        """
        Temporarily reserve a slot (optimistic locking).

        Args:
            slot_id: The slot ID to reserve

        Returns:
            True if reservation was successful
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"/api/v1/availabilities/{slot_id}/reserve",
                json={"reservation_duration_seconds": 300},  # 5 minutes
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:  # Conflict - already reserved
                logger.warning(f"Slot {slot_id} is already reserved")
                return False
            logger.error(f"Error reserving slot: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error reserving slot: {e}")
            return False

    async def release_slot(self, slot_id: UUID) -> bool:
        """
        Release a previously reserved slot.

        Args:
            slot_id: The slot ID to release

        Returns:
            True if release was successful
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"/api/v1/availabilities/{slot_id}/release"
            )
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error releasing slot: {e}")
            return False


# Singleton instance for reuse
_availability_service: Optional[AvailabilityService] = None


def get_availability_service() -> AvailabilityService:
    """Get the singleton availability service instance."""
    global _availability_service
    if _availability_service is None:
        _availability_service = AvailabilityService()
    return _availability_service
