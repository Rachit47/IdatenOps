"""Deterministic checks for a proposed test-drive booking.

This is a preflight policy check only. It never reserves a slot and cannot
replace the fresh reads, row locks, conflict checks, and transaction required
when an operator approves a proposal.
"""

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from idatenops.leads.types import (
    ActivityDirection,
    ActivityType,
    ContactPermission,
    LeadActivityEvidence,
)


class ListingStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"


class InspectionStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class SlotStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class BookingBlockerCode(StrEnum):
    CONTACT_PERMISSION_UNKNOWN = "contact_permission_unknown"
    CONTACT_PERMISSION_DO_NOT_CONTACT = "contact_permission_do_not_contact"
    MISSING_INBOUND_REQUEST = "missing_inbound_test_drive_request"
    REQUEST_WITHDRAWN = "test_drive_request_withdrawn"
    VEHICLE_LOCATION_MISMATCH = "vehicle_location_mismatch"
    VEHICLE_NOT_AVAILABLE = "vehicle_not_available"
    VEHICLE_NOT_INSPECTED = "vehicle_not_inspected"
    SALESPERSON_INACTIVE = "salesperson_inactive"
    SALESPERSON_NOT_ELIGIBLE = "salesperson_not_eligible"
    SALESPERSON_LOCATION_MISMATCH = "salesperson_location_mismatch"
    SLOT_LOCATION_MISMATCH = "slot_location_mismatch"
    SLOT_CLOSED = "slot_closed"
    SLOT_NOT_IN_FUTURE = "slot_not_in_future"
    SLOT_WINDOW_INVALID = "slot_window_invalid"
    SLOT_DURATION_INVALID = "slot_duration_invalid"
    TURNAROUND_BUFFER_INVALID = "turnaround_buffer_invalid"
    VEHICLE_HAS_UNRESOLVED_CHECKOUT = "vehicle_has_unresolved_checkout"
    VEHICLE_SLOT_CONFLICT = "vehicle_slot_conflict"
    SALESPERSON_SLOT_CONFLICT = "salesperson_slot_conflict"


class EligibilityBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: BookingBlockerCode
    message: str


class ListingSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing_id: int = Field(gt=0)
    location_id: int = Field(gt=0)
    listing_status: ListingStatus
    inspection_status: InspectionStatus


class SalespersonSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_member_id: int = Field(gt=0)
    location_id: int = Field(gt=0)
    is_active: bool
    # This field is backed by migration 001; it is absent from the supplied schema.
    is_test_drive_eligible: bool


class SlotSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    test_drive_slot_id: int = Field(gt=0)
    location_id: int = Field(gt=0)
    starts_at_utc: datetime
    ends_at_utc: datetime
    status: SlotStatus
    turnaround_buffer_minutes: int = Field(ge=0, le=120)

    @field_validator("starts_at_utc", "ends_at_utc")
    @classmethod
    def normalize_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("slot timestamps must include a timezone")
        return value.astimezone(timezone.utc)


class BookingPolicy(BaseModel):
    """Configurable slot rules. Defaults match the supplied design."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    appointment_minutes: int = Field(default=30, gt=0, le=240)
    turnaround_buffer_minutes: int = Field(default=15, ge=0, le=120)


class BookingEligibilitySnapshot(BaseModel):
    """Read-only facts collected for one lead and one candidate slot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lead_id: int = Field(gt=0)
    lead_location_id: int = Field(gt=0)
    contact_permission: ContactPermission
    activities: tuple[LeadActivityEvidence, ...] = ()
    listing: ListingSnapshot
    salesperson: SalespersonSnapshot
    slot: SlotSnapshot
    vehicle_has_unresolved_checkout: bool = False
    vehicle_has_active_conflict: bool = False
    salesperson_has_active_conflict: bool = False


class TestDriveEligibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligible: bool
    blockers: tuple[EligibilityBlocker, ...]
    matched_request_activity_id: int | None
    checked_at_utc: datetime
    reservation_created: bool = False


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now_utc must include a timezone")
    return value.astimezone(timezone.utc)


def evaluate_test_drive_eligibility(
    snapshot: BookingEligibilitySnapshot,
    *,
    now_utc: datetime | None = None,
    policy: BookingPolicy | None = None,
) -> TestDriveEligibilityResult:
    """Return blockers for a candidate; never writes or reserves business data."""
    checked_at = _as_utc(now_utc or datetime.now(timezone.utc))
    active_policy = policy or BookingPolicy()
    blockers: list[EligibilityBlocker] = []

    def block(code: BookingBlockerCode, message: str) -> None:
        blockers.append(EligibilityBlocker(code=code, message=message))

    if snapshot.contact_permission is ContactPermission.UNKNOWN:
        block(
            BookingBlockerCode.CONTACT_PERMISSION_UNKNOWN,
            "Contact permission is unknown; staff must resolve it before booking.",
        )
    elif snapshot.contact_permission is ContactPermission.DO_NOT_CONTACT:
        block(
            BookingBlockerCode.CONTACT_PERMISSION_DO_NOT_CONTACT,
            "Do-not-contact status blocks a test-drive booking proposal.",
        )

    # Only a recorded inbound request for this same lead is valid evidence.
    intent_events = [
        item
        for item in snapshot.activities
        if item.lead_id == snapshot.lead_id
        and item.activity_type
        in {
            ActivityType.TEST_DRIVE_REQUESTED,
            ActivityType.TEST_DRIVE_REQUEST_WITHDRAWN,
        }
        and item.occurred_at_utc <= checked_at
    ]
    latest_intent_event = max(
        intent_events,
        key=lambda item: (item.occurred_at_utc, item.activity_id),
        default=None,
    )
    matched_request_id: int | None = None
    if latest_intent_event is None:
        block(
            BookingBlockerCode.MISSING_INBOUND_REQUEST,
            "No recorded, current test-drive request was found for this lead.",
        )
    elif latest_intent_event.activity_type is ActivityType.TEST_DRIVE_REQUEST_WITHDRAWN:
        block(
            BookingBlockerCode.REQUEST_WITHDRAWN,
            "The latest recorded test-drive intent was withdrawn.",
        )
    elif latest_intent_event.direction is not ActivityDirection.INBOUND:
        block(
            BookingBlockerCode.MISSING_INBOUND_REQUEST,
            "The latest request record is not inbound activity.",
        )
    else:
        matched_request_id = latest_intent_event.activity_id

    listing = snapshot.listing
    if listing.location_id != snapshot.lead_location_id:
        block(
            BookingBlockerCode.VEHICLE_LOCATION_MISMATCH,
            "The vehicle must be at the lead's retail location.",
        )
    if listing.listing_status is not ListingStatus.AVAILABLE:
        block(
            BookingBlockerCode.VEHICLE_NOT_AVAILABLE,
            "The vehicle listing is not available.",
        )
    if listing.inspection_status is not InspectionStatus.PASSED:
        block(
            BookingBlockerCode.VEHICLE_NOT_INSPECTED,
            "The vehicle must have a passed inspection.",
        )

    salesperson = snapshot.salesperson
    if not salesperson.is_active:
        block(
            BookingBlockerCode.SALESPERSON_INACTIVE,
            "The assigned salesperson is not active.",
        )
    if not salesperson.is_test_drive_eligible:
        block(
            BookingBlockerCode.SALESPERSON_NOT_ELIGIBLE,
            "The assigned salesperson is not marked as test-drive eligible.",
        )
    if salesperson.location_id != snapshot.lead_location_id:
        block(
            BookingBlockerCode.SALESPERSON_LOCATION_MISMATCH,
            "The salesperson must belong to the lead's retail location.",
        )

    slot = snapshot.slot
    if slot.location_id != snapshot.lead_location_id:
        block(
            BookingBlockerCode.SLOT_LOCATION_MISMATCH,
            "The appointment slot must belong to the lead's retail location.",
        )
    if slot.status is not SlotStatus.OPEN:
        block(BookingBlockerCode.SLOT_CLOSED, "The appointment slot is closed.")
    if slot.starts_at_utc <= checked_at:
        block(
            BookingBlockerCode.SLOT_NOT_IN_FUTURE,
            "The appointment slot must start in the future.",
        )
    if slot.ends_at_utc <= slot.starts_at_utc:
        block(
            BookingBlockerCode.SLOT_WINDOW_INVALID,
            "The slot end time must be later than its start time.",
        )
    elif slot.ends_at_utc - slot.starts_at_utc != timedelta(
        minutes=active_policy.appointment_minutes
    ):
        block(
            BookingBlockerCode.SLOT_DURATION_INVALID,
            f"The appointment must last {active_policy.appointment_minutes} minutes.",
        )
    if slot.turnaround_buffer_minutes != active_policy.turnaround_buffer_minutes:
        block(
            BookingBlockerCode.TURNAROUND_BUFFER_INVALID,
            f"The vehicle turnaround buffer must be {active_policy.turnaround_buffer_minutes} minutes.",
        )

    if snapshot.vehicle_has_unresolved_checkout:
        block(
            BookingBlockerCode.VEHICLE_HAS_UNRESOLVED_CHECKOUT,
            "The vehicle has an unresolved checkout and stays unavailable until staff records its return.",
        )
    if snapshot.vehicle_has_active_conflict:
        block(
            BookingBlockerCode.VEHICLE_SLOT_CONFLICT,
            "The vehicle has a conflicting booking or hold for this slot.",
        )
    if snapshot.salesperson_has_active_conflict:
        block(
            BookingBlockerCode.SALESPERSON_SLOT_CONFLICT,
            "The salesperson has a conflicting booking for this slot.",
        )

    return TestDriveEligibilityResult(
        eligible=not blockers,
        blockers=tuple(blockers),
        matched_request_activity_id=matched_request_id,
        checked_at_utc=checked_at,
        reservation_created=False,
    )
