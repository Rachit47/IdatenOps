"""Shared lead types used by business rules.

These are validated application snapshots, not SQLAlchemy table models.
The database adapter will map MySQL rows into these types in a later phase.
"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContactPermission(StrEnum):
    PERMITTED = "permitted"
    UNKNOWN = "unknown"
    DO_NOT_CONTACT = "do_not_contact"


class ActivityType(StrEnum):
    INBOUND_ENQUIRY = "inbound_enquiry"
    CALL_ATTEMPT = "call_attempt"
    CALL_CONNECTED = "call_connected"
    MESSAGE_RECEIVED = "message_received"
    WEBSITE_CHAT = "website_chat"
    INTERNAL_NOTE = "internal_note"
    TEST_DRIVE_REQUESTED = "test_drive_requested"
    TEST_DRIVE_REQUEST_WITHDRAWN = "test_drive_request_withdrawn"


class ActivityDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class LeadActivityEvidence(BaseModel):
    """Small, safe slice of a lead's history used to check buyer intent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    activity_id: int = Field(gt=0)
    lead_id: int = Field(gt=0)
    activity_type: ActivityType
    direction: ActivityDirection
    occurred_at_utc: datetime

    @field_validator("occurred_at_utc")
    @classmethod
    def require_aware_utc_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at_utc must include a timezone")
        return value.astimezone(timezone.utc)
