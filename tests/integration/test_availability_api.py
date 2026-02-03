"""
Integration tests for the Availability API.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.availability_server import app
from src.api.availability_server import store as availability_store

# Use a valid motive ID from the config
VALID_MOTIVE_ID = "first_consultation"


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the availability store before each test."""
    availability_store._slots.clear()
    availability_store._reservations.clear()
    availability_store._bookings.clear()
    availability_store._initialized = False
    availability_store._initialize_sample_slots()
    yield
    availability_store._slots.clear()
    availability_store._reservations.clear()
    availability_store._bookings.clear()


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Health endpoint should return OK."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAvailabilityEndpoint:
    """Test availability listing endpoint."""

    @pytest.mark.asyncio
    async def test_get_availabilities(self, client):
        """Should return list of available slots."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        assert isinstance(data["slots"], list)

    @pytest.mark.asyncio
    async def test_availabilities_have_required_fields(self, client):
        """Each slot should have required fields."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        data = response.json()

        if data["slots"]:
            slot = data["slots"][0]
            assert "id" in slot
            assert "start_time" in slot
            assert "practitioner_name" in slot

    @pytest.mark.asyncio
    async def test_filter_by_motive(self, client):
        """Should filter slots by motive."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client):
        """Should filter slots by date range."""
        now = datetime.now()
        start = now.isoformat()
        end = (now + timedelta(days=7)).isoformat()
        response = await client.get(
            f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}&start_date={start}&end_date={end}"
        )
        assert response.status_code == 200


class TestReservationEndpoint:
    """Test slot reservation endpoint."""

    @pytest.mark.asyncio
    async def test_reserve_available_slot(self, client):
        """Should reserve an available slot."""
        # Get available slots
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        # Reserve the slot
        response = await client.post(f"/api/v1/availabilities/{slot_id}/reserve")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_reserve_nonexistent_slot(self, client):
        """Should fail to reserve non-existent slot."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/availabilities/{fake_id}/reserve")
        # Should return 409 Conflict for unavailable/missing slots
        assert response.status_code in (404, 409)

    @pytest.mark.asyncio
    async def test_double_reservation_fails(self, client):
        """Should not allow double reservation of same slot."""
        # Get available slots
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        # First reservation
        response1 = await client.post(f"/api/v1/availabilities/{slot_id}/reserve")
        assert response1.json()["success"] is True

        # Second reservation should fail
        response2 = await client.post(f"/api/v1/availabilities/{slot_id}/reserve")
        assert response2.status_code == 409


class TestReleaseEndpoint:
    """Test slot release endpoint."""

    @pytest.mark.asyncio
    async def test_release_reserved_slot(self, client):
        """Should release a reserved slot."""
        # Get and reserve a slot
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        await client.post(f"/api/v1/availabilities/{slot_id}/reserve")

        # Release
        response = await client.post(f"/api/v1/availabilities/{slot_id}/release")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_release_allows_new_reservation(self, client):
        """After release, slot should be available again."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        # Reserve then release
        await client.post(f"/api/v1/availabilities/{slot_id}/reserve")
        await client.post(f"/api/v1/availabilities/{slot_id}/release")

        # Should be able to reserve again
        response = await client.post(f"/api/v1/availabilities/{slot_id}/reserve")
        assert response.json()["success"] is True


class TestBookingEndpoint:
    """Test booking confirmation endpoint."""

    @pytest.mark.asyncio
    async def test_book_reserved_slot(self, client):
        """Should confirm booking for reserved slot."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        # Reserve first
        await client.post(f"/api/v1/availabilities/{slot_id}/reserve")

        # Book
        response = await client.post(f"/api/v1/availabilities/{slot_id}/book")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_book_unreserved_slot(self, client):
        """Should succeed booking even without prior reservation."""
        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        # Book directly (the API allows this)
        response = await client.post(f"/api/v1/availabilities/{slot_id}/book")
        assert response.status_code == 200


class TestConcurrency:
    """Test concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_reservations(self, client):
        """Only one concurrent reservation should succeed."""
        import asyncio

        response = await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")
        slots = response.json()["slots"]

        if not slots:
            pytest.skip("No slots available for test")

        slot_id = slots[0]["id"]

        async def try_reserve():
            return await client.post(f"/api/v1/availabilities/{slot_id}/reserve")

        # Try 5 concurrent reservations
        results = await asyncio.gather(
            *[try_reserve() for i in range(5)]
        )

        # Only one should succeed (200), others should get 409
        successes = sum(1 for r in results if r.status_code == 200)
        assert successes == 1

    @pytest.mark.asyncio
    async def test_high_read_concurrency(self, client):
        """Should handle many concurrent reads."""
        import asyncio

        async def get_availabilities():
            return await client.get(f"/api/v1/availabilities?motive_id={VALID_MOTIVE_ID}")

        # 50 concurrent reads
        results = await asyncio.gather(
            *[get_availabilities() for _ in range(50)]
        )

        # All should succeed
        assert all(r.status_code == 200 for r in results)
