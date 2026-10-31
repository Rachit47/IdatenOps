
"""Tests for Agent Savitar's intent classification."""

import pytest
from pydantic import ValidationError

from idatenops.agent.classification import (
    validate_classification_evidence,
)
from idatenops.agent.models import (
    IntentClassification,
    LeadIntent,
)


def test_classification_accepts_valid_intent() -> None:
    result = IntentClassification(
        intent=LeadIntent.TEST_DRIVE,
        reason="The buyer requested a test drive.",
        supporting_activity_ids=[901],
    )

    assert result.intent == LeadIntent.TEST_DRIVE
    assert result.supporting_activity_ids == [901]


def test_classification_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        IntentClassification(
            intent="test_drive",
            reason="The buyer requested a test drive.",
            supporting_activity_ids=[901],
            booking_status="available",
        )


def test_classification_evidence_accepts_matching_id() -> None:
    result = IntentClassification(
        intent=LeadIntent.TEST_DRIVE,
        reason="The buyer requested a test drive.",
        supporting_activity_ids=[901],
    )

    evidence = [
        {"activity_id": 901},
        {"activity_id": 902},
    ]

    assert validate_classification_evidence(
        result,
        evidence,
    ) is True


def test_classification_evidence_rejects_unknown_id() -> None:
    result = IntentClassification(
        intent=LeadIntent.TEST_DRIVE,
        reason="The buyer requested a test drive.",
        supporting_activity_ids=[999],
    )

    evidence = [
        {"activity_id": 901},
    ]

    assert validate_classification_evidence(
        result,
        evidence,
    ) is False


def test_classification_evidence_rejects_empty_citations() -> None:
    result = IntentClassification(
        intent=LeadIntent.HUMAN_REVIEW,
        reason="There is not enough evidence.",
    )

    assert validate_classification_evidence(
        result,
        [{"activity_id": 901}],
    ) is False
