from datetime import datetime, timezone
from unittest.mock import Mock

from sqlalchemy.orm import Session

from idatenops.test_drives import booking_eligibility_service
from idatenops.test_drives.test_drive_booking_eligibility import (
    BookingEligibilitySnapshot,
    ContactPermission,
    InspectionStatus,
    ListingSnapshot,
    ListingStatus,
    SalespersonSnapshot,
    SlotSnapshot,
    SlotStatus,
)


def test_service_loads_snapshot_and_checks_eligibility(monkeypatch) -> None:
    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)

    snapshot = BookingEligibilitySnapshot(
        lead_id=1,
        lead_location_id=10,
        contact_permission=ContactPermission.PERMITTED,
        activities=(),
        listing=ListingSnapshot(
            listing_id=50,
            location_id=10,
            listing_status=ListingStatus.AVAILABLE,
            inspection_status=InspectionStatus.PASSED,
        ),
        salesperson=SalespersonSnapshot(
            team_member_id=7,
            location_id=10,
            is_active=True,
            is_test_drive_eligible=True,
        ),
        slot=SlotSnapshot(
            test_drive_slot_id=90,
            location_id=10,
            starts_at_utc=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
            ends_at_utc=datetime(2026, 10, 26, 12, 30, tzinfo=timezone.utc),
            status=SlotStatus.OPEN,
            turnaround_buffer_minutes=15,
        ),
    )

    loader = Mock(return_value=snapshot)
    monkeypatch.setattr(
        booking_eligibility_service,
        "load_booking_eligibility_snapshot",
        loader,
    )

    result = booking_eligibility_service.check_test_drive_eligibility(
        Mock(spec=Session),
        lead_id=1,
        listing_id=50,
        salesperson_id=7,
        slot_id=90,
        now_utc=now,
    )

    loader.assert_called_once()
    assert result.eligible is False
    assert result.reservation_created is False