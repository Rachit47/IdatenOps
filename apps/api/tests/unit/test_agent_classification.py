
"""Tests for Agent Savitar's activity classification."""

from idatenops.agent.classification import (
    classify_activity_evidence,
)
from idatenops.agent.models import LeadIntent


def test_inbound_test_drive_request_is_classified() -> None:
    evidence = [
        {
            "activity_id": 901,
            "activity_type": "test_drive_requested",
            "direction": "inbound",
            "occurred_at_utc": "2026-10-25T10:30:00+00:00",
        }
    ]

    result = classify_activity_evidence(evidence)

    assert result.intent == LeadIntent.TEST_DRIVE
    assert result.supporting_activity_ids == [901]


def test_test_drive_withdrawal_overrides_old_request() -> None:
    evidence = [
        {
            "activity_id": 901,
            "activity_type": "test_drive_requested",
            "direction": "inbound",
            "occurred_at_utc": "2026-10-25T10:30:00+00:00",
        },
        {
            "activity_id": 902,
            "activity_type": "test_drive_request_withdrawn",
            "direction": "inbound",
            "occurred_at_utc": "2026-10-26T10:30:00+00:00",
        },
    ]

    result = classify_activity_evidence(evidence)

    assert result.intent == LeadIntent.FOLLOW_UP
    assert result.supporting_activity_ids == [902]


def test_outbound_test_drive_event_is_not_buyer_request() -> None:
    evidence = [
        {
            "activity_id": 903,
            "activity_type": "test_drive_requested",
            "direction": "outbound",
            "occurred_at_utc": "2026-10-25T10:30:00+00:00",
        }
    ]

    result = classify_activity_evidence(evidence)

    assert result.intent == LeadIntent.FOLLOW_UP


def test_empty_evidence_requires_human_review() -> None:
    result = classify_activity_evidence([])

    assert result.intent == LeadIntent.HUMAN_REVIEW
    assert result.supporting_activity_ids == []


def test_latest_request_after_withdrawal_is_active() -> None:
    evidence = [
        {
            "activity_id": 902,
            "activity_type": "test_drive_request_withdrawn",
            "direction": "inbound",
            "occurred_at_utc": "2026-10-25T10:30:00+00:00",
        },
        {
            "activity_id": 903,
            "activity_type": "test_drive_requested",
            "direction": "inbound",
            "occurred_at_utc": "2026-10-26T10:30:00+00:00",
        },
    ]

    result = classify_activity_evidence(evidence)

    assert result.intent == LeadIntent.TEST_DRIVE
    assert result.supporting_activity_ids == [903]
