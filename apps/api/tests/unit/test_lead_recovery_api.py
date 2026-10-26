"""Tests for the overdue-lead API."""

from datetime import datetime, timezone
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from idatenops.infrastructure.database import get_db_session
from idatenops.main import app


def test_overdue_leads_endpoint_returns_json_summaries() -> None:
    # Arrange: prepare a demo database session and one sample row.
    demo_session = Mock(spec=Session)

    demo_session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "lead_id": 101,
            "lead_code": "LEAD-101",
            "stage": "qualified",
            "location_id": 10,
            "next_follow_up_at_utc": datetime(
                2026, 10, 22, 10, 0
            ),
            "prospect_name": "Rajkumar Hirani",
            "prospect_city": "Delhi",
            "contact_permission": "permitted",
            "assigned_team_member_id": 7,
            "assigned_salesperson_name": "Neha Sharma",
        }
    ]

    def override_database_session():
        yield demo_session

    app.dependency_overrides[get_db_session] = override_database_session

    try:
        # Act: send a real HTTP request through FastAPI.
        client = TestClient(app)
        response = client.get(
            "/api/v1/lead-recovery/overdue?limit=25"
        )
    finally:
        # Always remove the test override.
        app.dependency_overrides.pop(get_db_session, None)

    # Assert: check the response.
    assert response.status_code == 200

    result = response.json()

    assert len(result) == 1
    assert result[0]["lead_code"] == "LEAD-101"
    assert result[0]["prospect_name"] == "Rajkumar Hirani"
    assert result[0]["contact_permission"] == "permitted"
    assert result[0]["assigned_salesperson_name"] == "Neha Sharma"
    assert result[0]["next_follow_up_at_utc"].endswith(("+00:00", "Z"))