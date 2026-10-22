"""HTTP routes for health and local rule exercises.

The development policy-check route accepts a caller-supplied snapshot. It is
not a booking endpoint, must not be used for authorization, and must not be
exposed to the public internet. Production endpoints will load facts from the
MySQL repositories and repeat all checks during approval.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from idatenops.test_drives.test_drive_booking_eligibility import (
    TestDriveEligibilityResult,
    BookingEligibilitySnapshot,
    evaluate_test_drive_eligibility,
)

router = APIRouter()
dev_router = APIRouter()


@router.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "idatenops-api"}


@dev_router.post(
    "/api/v1/dev/test-drive-eligibility",
    response_model=TestDriveEligibilityResult,
    tags=["Development"],
    summary="Evaluate a synthetic booking snapshot without reserving anything",
)
def check_test_drive_eligibility(
    snapshot: BookingEligibilitySnapshot,
) -> TestDriveEligibilityResult:
    return evaluate_test_drive_eligibility(
        snapshot,
        now_utc=datetime.now(timezone.utc),
    )
