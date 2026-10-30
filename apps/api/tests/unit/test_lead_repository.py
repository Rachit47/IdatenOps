
"""Tests for shared lead database queries."""

from datetime import datetime
from unittest.mock import Mock

from sqlalchemy.orm import Session

from idatenops.leads.lead_repository import (
    get_lead_activity_history,
)


def test_get_lead_activity_history_maps_database_columns() -> None:
    session = Mock(spec=Session)
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "activity_id": 901,
            "lead_id": 101,
            "activity_type": "test_drive_requested",
            "direction": "inbound",
            "occurred_at_utc": datetime(2026, 10, 25, 10, 30),
        }
    ]

    activities = get_lead_activity_history(
        session,
        lead_id=101,
        limit=20,
    )

    assert len(activities) == 1
    assert activities[0].activity_id == 901
    assert activities[0].lead_id == 101
    assert activities[0].activity_type.value == "test_drive_requested"
    assert activities[0].occurred_at_utc.isoformat() == (
        "2026-10-25T10:30:00+00:00"
    )

    statement, parameters = session.execute.call_args.args
    assert "FROM lead_activities" in str(statement)
    assert parameters == {"lead_id": 101, "limit": 20}
