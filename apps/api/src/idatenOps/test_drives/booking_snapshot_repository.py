"""Load database facts for test-drive eligibility checks."""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from idatenops.leads.lead_models import (
    ActivityDirection,
    ActivityType,
    ContactPermission,
    LeadActivityEvidence,
)
from idatenops.test_drives.test_drive_booking_eligibility import (
    BookingEligibilitySnapshot,
    InspectionStatus,
    ListingSnapshot,
    ListingStatus,
    SalespersonSnapshot,
    SlotSnapshot,
    SlotStatus,
)


# Read the lead and the three resources being considered.
BOOKING_FACTS_QUERY = text("""
    SELECT
        l.lead_id,
        l.location_id AS lead_location_id,
        p.contact_permission,

        v.listing_id,
        v.location_id AS vehicle_location_id,
        v.listing_status,
        v.inspection_status,

        tm.team_member_id,
        tm.location_id AS salesperson_location_id,
        tm.is_active AS salesperson_is_active,
        tm.is_test_drive_eligible,

        s.test_drive_slot_id,
        s.location_id AS slot_location_id,
        s.starts_at_utc,
        s.ends_at_utc,
        s.slot_status,
        s.turnaround_buffer_minutes

    FROM sales_leads AS l
    JOIN prospects AS p
        ON p.prospect_id = l.prospect_id

    LEFT JOIN vehicle_listings AS v
        ON v.listing_id = :listing_id

    LEFT JOIN team_members AS tm
        ON tm.team_member_id = :salesperson_id

    LEFT JOIN test_drive_slots AS s
        ON s.test_drive_slot_id = :slot_id

    WHERE l.lead_id = :lead_id
""")


# Read only the activity types used to prove test-drive intent.
REQUEST_ACTIVITY_QUERY = text("""
    SELECT
        lead_activity_id,
        lead_id,
        activity_type,
        direction,
        occurred_at
    FROM lead_activities
    WHERE lead_id = :lead_id
      AND activity_type IN (
          'test_drive_requested',
          'test_drive_request_withdrawn'
      )
    ORDER BY occurred_at ASC, lead_activity_id ASC
""")


UNRESOLVED_CHECKOUT_QUERY = text("""
    SELECT EXISTS (
        SELECT 1
        FROM test_drive_bookings
        WHERE listing_id = :listing_id
          AND booking_status = 'checked_out'
          AND actual_return_at_utc IS NULL
    )
""")


VEHICLE_CONFLICT_QUERY = text("""
    SELECT EXISTS (
        SELECT 1
        FROM test_drive_bookings AS b
        JOIN test_drive_slots AS booked_slot
            ON booked_slot.test_drive_slot_id = b.test_drive_slot_id
        JOIN test_drive_slots AS candidate_slot
            ON candidate_slot.test_drive_slot_id = :slot_id
        WHERE b.listing_id = :listing_id
          AND b.booking_status IN ('scheduled', 'checked_out')
          AND booked_slot.starts_at_utc < DATE_ADD(
              candidate_slot.ends_at_utc,
              INTERVAL candidate_slot.turnaround_buffer_minutes MINUTE
          )
          AND DATE_ADD(
              booked_slot.ends_at_utc,
              INTERVAL booked_slot.turnaround_buffer_minutes MINUTE
          ) > candidate_slot.starts_at_utc
    )
""")


SALESPERSON_CONFLICT_QUERY = text("""
    SELECT EXISTS (
        SELECT 1
        FROM test_drive_bookings AS b
        JOIN test_drive_slots AS booked_slot
            ON booked_slot.test_drive_slot_id = b.test_drive_slot_id
        JOIN test_drive_slots AS candidate_slot
            ON candidate_slot.test_drive_slot_id = :slot_id
        WHERE b.assigned_team_member_id = :salesperson_id
          AND b.booking_status IN ('scheduled', 'checked_out')
          AND booked_slot.starts_at_utc < DATE_ADD(
              candidate_slot.ends_at_utc,
              INTERVAL candidate_slot.turnaround_buffer_minutes MINUTE
          )
          AND DATE_ADD(
              booked_slot.ends_at_utc,
              INTERVAL booked_slot.turnaround_buffer_minutes MINUTE
          ) > candidate_slot.starts_at_utc
    )
""")


def _as_utc(value: datetime) -> datetime:
    """Treat MySQL's timezone-free DATETIME values as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_booking_eligibility_snapshot(
    session: Session,
    *,
    lead_id: int,
    listing_id: int,
    salesperson_id: int,
    slot_id: int,
) -> BookingEligibilitySnapshot:
    """Collect the current facts needed by the eligibility rules."""

    params = {
        "lead_id": lead_id,
        "listing_id": listing_id,
        "salesperson_id": salesperson_id,
        "slot_id": slot_id,
    }

    row = (
        session.execute(BOOKING_FACTS_QUERY, params)
        .mappings()
        .one_or_none()
    )

    if row is None:
        raise LookupError(f"Lead {lead_id} was not found.")

    if row["listing_id"] is None:
        raise LookupError(f"Vehicle listing {listing_id} was not found.")

    if row["team_member_id"] is None:
        raise LookupError(f"Salesperson {salesperson_id} was not found.")

    if row["test_drive_slot_id"] is None:
        raise LookupError(f"Test-drive slot {slot_id} was not found.")

    activity_rows = (
        session.execute(
            REQUEST_ACTIVITY_QUERY,
            {"lead_id": lead_id},
        )
        .mappings()
        .all()
    )

    activities = tuple(
        LeadActivityEvidence(
            activity_id=item["lead_activity_id"],
            lead_id=item["lead_id"],
            activity_type=ActivityType(item["activity_type"]),
            direction=ActivityDirection(item["direction"]),
            occurred_at_utc=_as_utc(item["occurred_at"]),
        )
        for item in activity_rows
    )

    vehicle_has_unresolved_checkout = bool(
        session.execute(
            UNRESOLVED_CHECKOUT_QUERY,
            {"listing_id": listing_id},
        ).scalar_one()
    )

    vehicle_has_active_conflict = bool(
        session.execute(VEHICLE_CONFLICT_QUERY, params).scalar_one()
    )

    salesperson_has_active_conflict = bool(
        session.execute(SALESPERSON_CONFLICT_QUERY, params).scalar_one()
    )

    return BookingEligibilitySnapshot(
        lead_id=row["lead_id"],
        lead_location_id=row["lead_location_id"],
        contact_permission=ContactPermission(row["contact_permission"]),
        activities=activities,
        listing=ListingSnapshot(
            listing_id=row["listing_id"],
            location_id=row["vehicle_location_id"],
            listing_status=ListingStatus(row["listing_status"]),
            inspection_status=InspectionStatus(row["inspection_status"]),
        ),
        salesperson=SalespersonSnapshot(
            team_member_id=row["team_member_id"],
            location_id=row["salesperson_location_id"],
            is_active=bool(row["salesperson_is_active"]),
            is_test_drive_eligible=bool(row["is_test_drive_eligible"]),
        ),
        slot=SlotSnapshot(
            test_drive_slot_id=row["test_drive_slot_id"],
            location_id=row["slot_location_id"],
            starts_at_utc=_as_utc(row["starts_at_utc"]),
            ends_at_utc=_as_utc(row["ends_at_utc"]),
            status=SlotStatus(row["slot_status"]),
            turnaround_buffer_minutes=row["turnaround_buffer_minutes"],
        ),
        vehicle_has_unresolved_checkout=vehicle_has_unresolved_checkout,
        vehicle_has_active_conflict=vehicle_has_active_conflict,
        salesperson_has_active_conflict=salesperson_has_active_conflict,
    )