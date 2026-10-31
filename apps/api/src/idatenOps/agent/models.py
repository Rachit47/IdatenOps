
"""Typed models used by Agent Savitar."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LeadIntent(str, Enum):
    """Supported lead-intent classifications."""

    TEST_DRIVE = "test_drive"
    FOLLOW_UP = "follow_up"
    HUMAN_REVIEW = "human_review"


class IntentClassification(BaseModel):
    """Structured classification based on lead activity evidence."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    intent: LeadIntent

    reason: str = Field(
        min_length=1,
        max_length=300,
    )

    supporting_activity_ids: list[int] = Field(
        default_factory=list,
    )
