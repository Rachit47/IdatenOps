from fastapi.testclient import TestClient

from idatenops.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "idatenops-api"}


def test_dev_policy_endpoint_evaluates_snapshot_without_booking() -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    payload = {
        "lead_id": 1,
        "lead_location_id": 10,
        "contact_permission": "permitted",
        "activities": [
            {
                "activity_id": 101,
                "lead_id": 1,
                "activity_type": "test_drive_requested",
                "direction": "inbound",
                "occurred_at_utc": (now - timedelta(minutes=5)).isoformat(),
            }
        ],
        "listing": {
            "listing_id": 50,
            "location_id": 10,
            "listing_status": "available",
            "inspection_status": "passed",
        },
        "salesperson": {
            "team_member_id": 7,
            "location_id": 10,
            "is_active": True,
            "is_test_drive_eligible": True,
        },
        "slot": {
            "test_drive_slot_id": 90,
            "location_id": 10,
            "starts_at_utc": (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
            "ends_at_utc": (now + timedelta(days=1)).replace(hour=10, minute=30, second=0, microsecond=0).isoformat(),
            "status": "open",
            "turnaround_buffer_minutes": 15,
        },
        "vehicle_has_unresolved_checkout": False,
        "vehicle_has_active_conflict": False,
        "salesperson_has_active_conflict": False,
    }
    response = client.post("/api/v1/dev/test-drive-eligibility", json=payload)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["eligible"] is True
    assert result["matched_request_activity_id"] == 101
    assert result["reservation_created"] is False
