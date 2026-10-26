"""Application service for checking test-drive eligibility."""

from datetime import datetime

from sqlalchemy.orm import Session

from idatenops.test_drives.booking_snapshot_repository import (
    load_booking_eligibility_snapshot,
)
from idatenops.test_drives.test_drive_booking_eligibility import (
    BookingPolicy,
    TestDriveEligibilityResult,
    evaluate_test_drive_eligibility,
)


def check_test_drive_eligibility(
    session: Session,
    *,
    lead_id: int,
    listing_id: int,
    salesperson_id: int,
    slot_id: int,
    now_utc: datetime | None = None,
    policy: BookingPolicy | None = None,
) -> TestDriveEligibilityResult:
    """Load current facts, then check them against booking rules."""

    snapshot = load_booking_eligibility_snapshot(
        session,
        lead_id=lead_id,
        listing_id=listing_id,
        salesperson_id=salesperson_id,
        slot_id=slot_id,
    )

    return evaluate_test_drive_eligibility(
        snapshot,
        now_utc=now_utc,
        policy=policy,
    )