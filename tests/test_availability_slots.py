"""
Test to verify availability slots are created for all days.
"""

import pytest
from datetime import datetime, timedelta
from collections import defaultdict

from src.api.availability_server import AvailabilityStore
from src.config import VISIT_MOTIVES


class TestAvailabilitySlotGeneration:
    """Test that slots are generated correctly for all days."""

    def test_slots_generated_for_multiple_days(self):
        """Verify slots exist for each weekday in the next 2 weeks."""
        store = AvailabilityStore()
        store._initialize_sample_slots()

        # Group slots by date
        slots_by_date = defaultdict(list)
        for slot in store.slots.values():
            date_str = slot.start_time.strftime("%Y-%m-%d")
            slots_by_date[date_str].append(slot)

        print(f"\n=== Slots by date ===")
        for date, slots in sorted(slots_by_date.items()):
            print(f"{date}: {len(slots)} slots")

        # Should have slots for at least 10 different days (14 days - 4 weekend days)
        assert len(slots_by_date) >= 10, f"Expected at least 10 days with slots, got {len(slots_by_date)}"

    def test_slots_for_specific_motive(self):
        """Check slots exist for glasses_renewal motive across multiple days."""
        store = AvailabilityStore()
        store._initialize_sample_slots()

        motive_id = "glasses_renewal"
        motive_slots = [s for s in store.slots.values() if s.motive_id == motive_id]

        # Group by date
        slots_by_date = defaultdict(list)
        for slot in motive_slots:
            date_str = slot.start_time.strftime("%Y-%m-%d")
            slots_by_date[date_str].append(slot)

        print(f"\n=== Slots for {motive_id} by date ===")
        for date, slots in sorted(slots_by_date.items()):
            print(f"{date}: {len(slots)} slots")

        assert len(slots_by_date) >= 10, f"Expected at least 10 days with slots for {motive_id}, got {len(slots_by_date)}"

    def test_total_slot_count(self):
        """Verify reasonable total number of slots."""
        store = AvailabilityStore()
        store._initialize_sample_slots()

        total_slots = len(store.slots)
        num_motives = len(VISIT_MOTIVES)
        num_practitioners = 3
        num_time_slots = 10  # 9:00, 9:30, 10:00, 10:30, 11:00, 14:00, 14:30, 15:00, 15:30, 16:00
        num_weekdays = 10  # ~10 weekdays in 2 weeks

        expected_min = num_motives * num_practitioners * num_time_slots * num_weekdays
        
        print(f"\n=== Total slots ===")
        print(f"Total: {total_slots}")
        print(f"Expected minimum: {expected_min}")
        print(f"Motives: {num_motives}, Practitioners: {num_practitioners}, Time slots: {num_time_slots}, Weekdays: ~{num_weekdays}")

        assert total_slots >= expected_min * 0.8, f"Expected at least {expected_min * 0.8} slots, got {total_slots}"

    def test_slots_have_various_times(self):
        """Verify slots exist at different times of day."""
        store = AvailabilityStore()
        store._initialize_sample_slots()

        # Get unique hours
        hours = set()
        for slot in store.slots.values():
            hours.add(slot.start_time.hour)

        print(f"\n=== Available hours ===")
        print(f"Hours: {sorted(hours)}")

        # Should have morning and afternoon slots
        assert 9 in hours, "Missing 9:00 slots"
        assert 14 in hours, "Missing 14:00 slots"
        assert len(hours) >= 6, f"Expected at least 6 different hours, got {len(hours)}"

    @pytest.mark.asyncio
    async def test_query_specific_date(self):
        """Test querying slots for a specific date."""
        store = AvailabilityStore()
        await store.initialize()
        
        # Query for Feb 5, 2026 (Thursday - should be a weekday)
        start = datetime(2026, 2, 5, 0, 0, 0)
        end = datetime(2026, 2, 5, 23, 59, 59)
        
        slots = await store.get_availabilities(
            motive_id="glasses_renewal",
            start_date=start,
            end_date=end,
            limit=20,
        )
        
        print(f"\n=== Slots for Feb 5, 2026 ===")
        print(f"Found {len(slots)} slots")
        for slot in slots[:5]:
            print(f"  {slot.start_time} - {slot.practitioner_name}")
        
        assert len(slots) > 0, "Expected slots for Feb 5, 2026"

    @pytest.mark.asyncio
    async def test_query_different_dates(self):
        """Test that multiple dates have slots."""
        store = AvailabilityStore()
        await store.initialize()
        
        dates_with_slots = []
        
        # Check multiple dates
        for day in [3, 4, 5, 6, 9, 10, 11, 12]:
            start = datetime(2026, 2, day, 0, 0, 0)
            end = datetime(2026, 2, day, 23, 59, 59)
            
            slots = await store.get_availabilities(
                motive_id="follow_up",
                start_date=start,
                end_date=end,
                limit=20,
            )
            
            if slots:
                dates_with_slots.append(day)
                print(f"Feb {day}: {len(slots)} slots")
        
        print(f"\n=== Dates with slots ===")
        print(f"Dates: {dates_with_slots}")
        
        # Should have slots for at least 6 different dates
        assert len(dates_with_slots) >= 6, f"Expected at least 6 dates with slots, got {len(dates_with_slots)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
