"""Tests for reading overdue leads."""

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from sqlalchemy.orm import Session

from idatenops.lead_recovery.overdue_lead_repository import (
    find_overdue_leads,
)


def test_find_overdue_leads_maps_rows_and_uses_utc() -> None:
    session = Mock(spec=Session)

    # MySQL DATETIME comes back without timezone information.
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "lead_id": 101,
            "lead_code": "LEAD-101",
            "stage": "qualified",
            "location_id": 10,
            "next_follow_up_at_utc": datetime(2026, 10, 22, 10, 0),
            "prospect_name": "Aarav Sharma",
            "prospect_city": "Delhi",
            "contact_permission": "permitted",
            "assigned_team_member_id": 7,
            "assigned_salesperson_name": "Neha Verma",
        }
    ]

    # 9:00 AM in India is 3:30 AM UTC.
    now_in_india = datetime(
        2026, 10, 23, 9, 0,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    leads = find_overdue_leads(
        session,
        now_utc=now_in_india,
        limit=25,
    )

    assert len(leads) == 1
    assert leads[0].lead_code == "LEAD-101"
    assert leads[0].contact_permission.value == "permitted"
    assert leads[0].next_follow_up_at_utc.tzinfo is not None

    statement, parameters = session.execute.call_args.args

    assert "l.stage NOT IN ('won', 'lost', 'invalid')" in str(statement)
    assert parameters["as_of_utc"] == datetime(2026, 10, 23, 3, 30)
    assert parameters["limit"] == 25