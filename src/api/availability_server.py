"""
Availability API Server.

A FastAPI-based microservice for managing appointment availabilities.
Designed for high concurrency with async operations and connection pooling.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from src.config import VISIT_MOTIVES

# ============================================================================
# Data Models
# ============================================================================


class SlotResponse(BaseModel):
    """Response model for an availability slot."""

    id: UUID
    start_time: datetime
    end_time: datetime
    practitioner_name: str
    practitioner_id: str
    motive_id: str
    is_available: bool

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    }


class AvailabilityResponse(BaseModel):
    """Response model for availability queries."""

    slots: List[SlotResponse]
    total: int
    motive_id: str


class ReservationRequest(BaseModel):
    """Request to temporarily reserve a slot."""

    reservation_duration_seconds: int = Field(default=300, ge=60, le=900)


class ReservationResponse(BaseModel):
    """Response for a reservation request."""

    success: bool
    slot_id: UUID
    expires_at: datetime


# ============================================================================
# In-Memory Data Store (Replace with Redis/PostgreSQL in production)
# ============================================================================


class AvailabilityStore:
    """
    In-memory availability store with thread-safe operations.

    In production, this should be replaced with:
    - Redis for reservations (with TTL support)
    - PostgreSQL for persistent slot storage
    """

    def __init__(self):
        self._slots: Dict[UUID, SlotResponse] = {}
        self._reservations: Dict[UUID, datetime] = {}  # slot_id -> expiry time
        self._bookings: Dict[UUID, bool] = {}  # completed bookings
        self._lock = asyncio.Lock()
        self._initialized = False

    # Public accessors for testing
    @property
    def slots(self) -> Dict[UUID, SlotResponse]:
        """Access to slots dictionary."""
        return self._slots

    @property
    def reservations(self) -> Dict[UUID, datetime]:
        """Access to reservations dictionary."""
        return self._reservations

    @property
    def bookings(self) -> Dict[UUID, bool]:
        """Access to bookings dictionary."""
        return self._bookings

    def _initialize_sample_slots(self) -> None:
        """Initialize sample slots synchronously for testing."""
        # Generate sample slots for the next 2 weeks
        practitioners = [
            ("Dr. Marie Dubois", "dr-dubois"),
            ("Dr. Pierre Martin", "dr-martin"),
            ("Dr. Sophie Bernard", "dr-bernard"),
        ]

        base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if base_date < datetime.now():
            base_date += timedelta(days=1)

        for motive in VISIT_MOTIVES:
            duration = timedelta(minutes=motive["duration_minutes"])

            # Generate slots for each day
            for day_offset in range(14):  # 2 weeks
                day = base_date + timedelta(days=day_offset)

                # Skip weekends
                if day.weekday() >= 5:
                    continue

                # Generate slots for each practitioner
                for prac_name, prac_id in practitioners:
                    # Morning slots: 9:00 - 12:00
                    # Afternoon slots: 14:00 - 18:00
                    time_slots = [
                        day.replace(hour=9, minute=0),
                        day.replace(hour=9, minute=30),
                        day.replace(hour=10, minute=0),
                        day.replace(hour=10, minute=30),
                        day.replace(hour=11, minute=0),
                        day.replace(hour=14, minute=0),
                        day.replace(hour=14, minute=30),
                        day.replace(hour=15, minute=0),
                        day.replace(hour=15, minute=30),
                        day.replace(hour=16, minute=0),
                    ]

                    for slot_time in time_slots:
                        slot_id = uuid4()
                        self._slots[slot_id] = SlotResponse(
                            id=slot_id,
                            start_time=slot_time,
                            end_time=slot_time + duration,
                            practitioner_name=prac_name,
                            practitioner_id=prac_id,
                            motive_id=motive["id"],
                            is_available=True,
                        )

        self._initialized = True

    async def initialize(self) -> None:
        """Initialize with sample availability data."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Generate sample slots for the next 2 weeks
            practitioners = [
                ("Dr. Marie Dubois", "dr-dubois"),
                ("Dr. Pierre Martin", "dr-martin"),
                ("Dr. Sophie Bernard", "dr-bernard"),
            ]

            base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            if base_date < datetime.now():
                base_date += timedelta(days=1)

            for motive in VISIT_MOTIVES:
                duration = timedelta(minutes=motive["duration_minutes"])

                # Generate slots for each day
                for day_offset in range(14):  # 2 weeks
                    day = base_date + timedelta(days=day_offset)

                    # Skip weekends
                    if day.weekday() >= 5:
                        continue

                    # Generate slots for each practitioner
                    for prac_name, prac_id in practitioners:
                        # Morning and afternoon slots
                        time_slots = [
                            day.replace(hour=9, minute=0),
                            day.replace(hour=10, minute=0),
                            day.replace(hour=11, minute=0),
                            day.replace(hour=14, minute=0),
                            day.replace(hour=15, minute=0),
                            day.replace(hour=16, minute=0),
                        ]

                        for slot_time in time_slots:
                            slot_id = uuid4()
                            self._slots[slot_id] = SlotResponse(
                                id=slot_id,
                                start_time=slot_time,
                                end_time=slot_time + duration,
                                practitioner_name=prac_name,
                                practitioner_id=prac_id,
                                motive_id=motive["id"],
                                is_available=True,
                            )

            self._initialized = True
            logger.info(f"Initialized {len(self._slots)} availability slots")

    async def get_availabilities(
        self,
        motive_id: str,
        start_date: datetime,
        end_date: datetime,
        practitioner_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[SlotResponse]:
        """Get available slots matching criteria."""
        await self._cleanup_expired_reservations()

        results = []
        for slot in self._slots.values():
            if not slot.is_available:
                continue
            if slot.motive_id != motive_id:
                continue
            if slot.start_time < start_date or slot.start_time > end_date:
                continue
            if practitioner_id and slot.practitioner_id != practitioner_id:
                continue
            if slot.id in self._reservations:
                continue  # Skip reserved slots

            results.append(slot)

        # Sort by start time
        results.sort(key=lambda s: s.start_time)

        # Apply offset and limit
        return results[offset : offset + limit]

    async def get_slot(self, slot_id: UUID) -> Optional[SlotResponse]:
        """Get a specific slot by ID."""
        return self._slots.get(slot_id)

    async def check_availability(self, slot_id: UUID) -> bool:
        """Check if a slot is available."""
        await self._cleanup_expired_reservations()

        slot = self._slots.get(slot_id)
        if not slot:
            return False
        if not slot.is_available:
            return False
        if slot_id in self._reservations:
            return False
        return True

    async def reserve_slot(
        self, slot_id: UUID, duration_seconds: int = 300
    ) -> Optional[datetime]:
        """
        Reserve a slot temporarily (optimistic locking).

        Returns the expiry time if successful, None if already reserved.
        """
        await self._cleanup_expired_reservations()

        async with self._lock:
            if slot_id in self._reservations:
                return None
            if slot_id not in self._slots:
                return None
            if not self._slots[slot_id].is_available:
                return None

            expiry = datetime.now() + timedelta(seconds=duration_seconds)
            self._reservations[slot_id] = expiry
            return expiry

    async def release_slot(self, slot_id: UUID) -> bool:
        """Release a reservation."""
        async with self._lock:
            if slot_id in self._reservations:
                del self._reservations[slot_id]
                return True
            return False

    async def book_slot(self, slot_id: UUID) -> bool:
        """Permanently book a slot (mark as unavailable)."""
        async with self._lock:
            if slot_id in self._slots:
                self._slots[slot_id].is_available = False
                if slot_id in self._reservations:
                    del self._reservations[slot_id]
                return True
            return False

    async def _cleanup_expired_reservations(self) -> None:
        """Remove expired reservations."""
        now = datetime.now()
        expired = [
            slot_id
            for slot_id, expiry in self._reservations.items()
            if expiry < now
        ]
        for slot_id in expired:
            del self._reservations[slot_id]


# Global store instance
store = AvailabilityStore()


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Availability API Server")
    await store.initialize()
    yield
    # Shutdown
    logger.info("Shutting down Availability API Server")


app = FastAPI(
    title="Vocca Availability API",
    description="API for managing medical appointment availabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/motives")
async def list_motives():
    """List all available visit motives."""
    return {"motives": VISIT_MOTIVES}


@app.get("/api/v1/availabilities", response_model=AvailabilityResponse)
async def get_availabilities(
    motive_id: str = Query(..., description="Visit motive ID"),
    start_date: datetime = Query(default=None, description="Start of search window"),
    end_date: datetime = Query(default=None, description="End of search window"),
    practitioner_id: Optional[str] = Query(default=None, description="Filter by practitioner"),
    limit: int = Query(default=5, ge=1, le=20, description="Maximum slots to return"),
    offset: int = Query(default=0, ge=0, description="Number of slots to skip"),
):
    """
    Get available appointment slots for a given motive.

    This endpoint is optimized for high concurrency with:
    - Async operations
    - Efficient filtering
    - Connection pooling (when using real database)
    """
    if start_date is None:
        start_date = datetime.now()
    if end_date is None:
        end_date = start_date + timedelta(weeks=2)

    slots = await store.get_availabilities(
        motive_id=motive_id,
        start_date=start_date,
        end_date=end_date,
        practitioner_id=practitioner_id,
        limit=limit,
        offset=offset,
    )

    return AvailabilityResponse(
        slots=slots,
        total=len(slots),
        motive_id=motive_id,
    )


@app.get("/api/v1/availabilities/{slot_id}", response_model=SlotResponse)
async def get_slot(slot_id: UUID):
    """Get a specific slot by ID."""
    slot = await store.get_slot(slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    is_available = await store.check_availability(slot_id)
    slot.is_available = is_available
    return slot


@app.post("/api/v1/availabilities/{slot_id}/reserve", response_model=ReservationResponse)
async def reserve_slot(slot_id: UUID, request: ReservationRequest = ReservationRequest()):
    """
    Temporarily reserve a slot.

    This creates an optimistic lock on the slot for a limited time,
    allowing the booking process to complete without race conditions.
    """
    expiry = await store.reserve_slot(slot_id, request.reservation_duration_seconds)

    if expiry is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot is already reserved or unavailable",
        )

    return ReservationResponse(
        success=True,
        slot_id=slot_id,
        expires_at=expiry,
    )


@app.post("/api/v1/availabilities/{slot_id}/release")
async def release_slot(slot_id: UUID):
    """Release a slot reservation."""
    released = await store.release_slot(slot_id)
    return {"success": released, "slot_id": str(slot_id)}


@app.post("/api/v1/availabilities/{slot_id}/book")
async def book_slot(slot_id: UUID):
    """Permanently book a slot."""
    booked = await store.book_slot(slot_id)

    if not booked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not book slot",
        )

    return {"success": True, "slot_id": str(slot_id)}


# ============================================================================
# Run Server
# ============================================================================


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the availability API server."""
    import uvicorn

    uvicorn.run(
        "src.api.availability_server:app",
        host=host,
        port=port,
        reload=False,
        workers=4,  # Multiple workers for concurrency
        loop="uvloop",  # High-performance event loop
        http="httptools",  # Fast HTTP parser
    )


if __name__ == "__main__":
    run_server()
