from datetime import datetime, timedelta, timezone

import pytest

from idatenops.leads.lead_models import (
    ActivityDirection,
    ActivityType,
    ContactPermission,
    LeadActivityEvidence,
)
from idatenops.test_drives.test_drive_booking_eligibility import (
    BookingBlockerCode,
    InspectionStatus,
    ListingStatus,
    SlotStatus,
    SlotSnapshot,
    BookingEligibilitySnapshot,
    ListingSnapshot,
    SalespersonSnapshot,
    evaluate_test_drive_eligibility,
)


NOW = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)


def _activity(
    activity_id: int = 101,
    *,
    lead_id: int = 1,
    activity_type: ActivityType = ActivityType.TEST_DRIVE_REQUESTED,
    direction: ActivityDirection = ActivityDirection.INBOUND,
    occurred_at_utc: datetime | None = None,
) -> LeadActivityEvidence:
    return LeadActivityEvidence(
        activity_id=activity_id,
        lead_id=lead_id,
        activity_type=activity_type,
        direction=direction,
        occurred_at_utc=occurred_at_utc or NOW - timedelta(minutes=20),
    )


def _snapshot(**overrides) -> BookingEligibilitySnapshot:
    values = {
        "lead_id": 1,
        "lead_location_id": 10,
        "contact_permission": ContactPermission.PERMITTED,
        "activities": (_activity(),),
        "listing": ListingSnapshot(
            listing_id=50,
            location_id=10,
            listing_status=ListingStatus.AVAILABLE,
            inspection_status=InspectionStatus.PASSED,
        ),
        "salesperson": SalespersonSnapshot(
            team_member_id=7,
            location_id=10,
            is_active=True,
            is_test_drive_eligible=True,
        ),
        "slot": SlotSnapshot(
            test_drive_slot_id=90,
            location_id=10,
            starts_at_utc=NOW + timedelta(hours=2),
            ends_at_utc=NOW + timedelta(hours=2, minutes=30),
            status=SlotStatus.OPEN,
            turnaround_buffer_minutes=15,
        ),
        "vehicle_has_unresolved_checkout": False,
        "vehicle_has_active_conflict": False,
        "salesperson_has_active_conflict": False,
    }
    values.update(overrides)
    return BookingEligibilitySnapshot(**values)


def test_valid_snapshot_is_eligible_but_does_not_reserve_slot() -> None:
    result = evaluate_test_drive_eligibility(_snapshot(), now_utc=NOW)

    assert result.eligible is True
    assert result.blockers == ()
    assert result.matched_request_activity_id == 101
    assert result.reservation_created is False
    assert result.checked_at_utc == NOW


@pytest.mark.parametrize(
    ("permission", "expected_code"),
    [
        (ContactPermission.UNKNOWN, BookingBlockerCode.CONTACT_PERMISSION_UNKNOWN),
        (
            ContactPermission.DO_NOT_CONTACT,
            BookingBlockerCode.CONTACT_PERMISSION_DO_NOT_CONTACT,
        ),
    ],
)
def test_booking_requires_permitted_contact_permission(permission, expected_code) -> None:
    result = evaluate_test_drive_eligibility(
        _snapshot(contact_permission=permission), now_utc=NOW
    )
    assert result.eligible is False
    assert expected_code in {blocker.code for blocker in result.blockers}


def test_general_interest_or_outbound_activity_is_not_request_evidence() -> None:
    snapshot = _snapshot(
        activities=(
            _activity(activity_type=ActivityType.INBOUND_ENQUIRY),
            _activity(
                activity_id=102,
                activity_type=ActivityType.TEST_DRIVE_REQUESTED,
                direction=ActivityDirection.OUTBOUND,
            ),
        )
    )
    result = evaluate_test_drive_eligibility(snapshot, now_utc=NOW)
    assert BookingBlockerCode.MISSING_INBOUND_REQUEST in {
        blocker.code for blocker in result.blockers
    }
    assert result.matched_request_activity_id is None


def test_request_must_belong_to_same_lead() -> None:
    result = evaluate_test_drive_eligibility(
        _snapshot(activities=(_activity(lead_id=999),)), now_utc=NOW
    )
    assert BookingBlockerCode.MISSING_INBOUND_REQUEST in {
        blocker.code for blocker in result.blockers
    }


def test_later_withdrawal_blocks_an_older_request() -> None:
    request = _activity(occurred_at_utc=NOW - timedelta(hours=2))
    withdrawal = _activity(
        activity_id=102,
        activity_type=ActivityType.TEST_DRIVE_REQUEST_WITHDRAWN,
        direction=ActivityDirection.INBOUND,
        occurred_at_utc=NOW - timedelta(minutes=5),
    )
    result = evaluate_test_drive_eligibility(
        _snapshot(activities=(request, withdrawal)), now_utc=NOW
    )
    assert BookingBlockerCode.REQUEST_WITHDRAWN in {
        blocker.code for blocker in result.blockers
    }


@pytest.mark.parametrize(
    ("listing_overrides", "expected_code"),
    [
        ({"location_id": 99}, BookingBlockerCode.VEHICLE_LOCATION_MISMATCH),
        (
            {"listing_status": ListingStatus.RESERVED},
            BookingBlockerCode.VEHICLE_NOT_AVAILABLE,
        ),
        (
            {"inspection_status": InspectionStatus.NEEDS_REVIEW},
            BookingBlockerCode.VEHICLE_NOT_INSPECTED,
        ),
    ],
)
def test_vehicle_must_be_local_available_and_inspected(listing_overrides, expected_code) -> None:
    listing = ListingSnapshot(
        listing_id=50,
        location_id=10,
        listing_status=ListingStatus.AVAILABLE,
        inspection_status=InspectionStatus.PASSED,
    ).model_copy(update=listing_overrides)
    result = evaluate_test_drive_eligibility(
        _snapshot(listing=listing), now_utc=NOW
    )
    assert expected_code in {blocker.code for blocker in result.blockers}


@pytest.mark.parametrize(
    ("salesperson_overrides", "expected_code"),
    [
        ({"is_active": False}, BookingBlockerCode.SALESPERSON_INACTIVE),
        (
            {"is_test_drive_eligible": False},
            BookingBlockerCode.SALESPERSON_NOT_ELIGIBLE,
        ),
        ({"location_id": 99}, BookingBlockerCode.SALESPERSON_LOCATION_MISMATCH),
    ],
)
def test_salesperson_must_be_active_eligible_and_local(salesperson_overrides, expected_code) -> None:
    salesperson = SalespersonSnapshot(
        team_member_id=7,
        location_id=10,
        is_active=True,
        is_test_drive_eligible=True,
    ).model_copy(update=salesperson_overrides)
    result = evaluate_test_drive_eligibility(
        _snapshot(salesperson=salesperson), now_utc=NOW
    )
    assert expected_code in {blocker.code for blocker in result.blockers}


@pytest.mark.parametrize(
    ("slot_overrides", "expected_code"),
    [
        ({"location_id": 99}, BookingBlockerCode.SLOT_LOCATION_MISMATCH),
        ({"status": SlotStatus.CLOSED}, BookingBlockerCode.SLOT_CLOSED),
        (
            {
                "starts_at_utc": NOW - timedelta(minutes=1),
                "ends_at_utc": NOW + timedelta(minutes=29),
            },
            BookingBlockerCode.SLOT_NOT_IN_FUTURE,
        ),
        (
            {"ends_at_utc": NOW + timedelta(hours=2, minutes=45)},
            BookingBlockerCode.SLOT_DURATION_INVALID,
        ),
        (
            {"turnaround_buffer_minutes": 10},
            BookingBlockerCode.TURNAROUND_BUFFER_INVALID,
        ),
    ],
)
def test_slot_must_be_open_future_local_and_match_demo_duration(slot_overrides, expected_code) -> None:
    slot = SlotSnapshot(
        test_drive_slot_id=90,
        location_id=10,
        starts_at_utc=NOW + timedelta(hours=2),
        ends_at_utc=NOW + timedelta(hours=2, minutes=30),
        status=SlotStatus.OPEN,
        turnaround_buffer_minutes=15,
    ).model_copy(update=slot_overrides)
    result = evaluate_test_drive_eligibility(_snapshot(slot=slot), now_utc=NOW)
    assert expected_code in {blocker.code for blocker in result.blockers}


@pytest.mark.parametrize(
    ("conflict_field", "expected_code"),
    [
        (
            "vehicle_has_unresolved_checkout",
            BookingBlockerCode.VEHICLE_HAS_UNRESOLVED_CHECKOUT,
        ),
        ("vehicle_has_active_conflict", BookingBlockerCode.VEHICLE_SLOT_CONFLICT),
        (
            "salesperson_has_active_conflict",
            BookingBlockerCode.SALESPERSON_SLOT_CONFLICT,
        ),
    ],
)
def test_any_active_resource_hold_blocks_a_proposal(conflict_field, expected_code) -> None:
    result = evaluate_test_drive_eligibility(
        _snapshot(**{conflict_field: True}), now_utc=NOW
    )
    assert expected_code in {blocker.code for blocker in result.blockers}


def test_naive_timestamp_is_rejected_at_the_boundary() -> None:
    with pytest.raises(ValueError, match="timezone"):
        _activity(occurred_at_utc=datetime(2026, 10, 22, 9, 0))

def test_future_request_is_not_valid_evidence_yet() -> None:
    future_request = _activity(
        occurred_at_utc=NOW + timedelta(minutes=1),
    )

    result = evaluate_test_drive_eligibility(
        _snapshot(activities=(future_request,)),
        now_utc=NOW,
    )

    blocker_codes = {blocker.code for blocker in result.blockers}

    assert BookingBlockerCode.MISSING_INBOUND_REQUEST in blocker_codes
    assert result.matched_request_activity_id is None
  
def test_slot_with_invalid_time_window_is_blocked() -> None:
    slot = SlotSnapshot(
        test_drive_slot_id=90,
        location_id=10,
        starts_at_utc=NOW + timedelta(hours=2),
        ends_at_utc=NOW + timedelta(hours=2),
        status=SlotStatus.OPEN,
        turnaround_buffer_minutes=15,
    )

    result = evaluate_test_drive_eligibility(
        _snapshot(slot=slot),
        now_utc=NOW,
    )

    blocker_codes = {blocker.code for blocker in result.blockers}

    assert BookingBlockerCode.SLOT_WINDOW_INVALID in blocker_codes
    assert result.eligible is False