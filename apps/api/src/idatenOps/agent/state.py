
"""State definition for Agent Savitar workflows."""

from typing import NotRequired, TypedDict


class SavitarState(TypedDict):
    """Data passed between Agent Savitar's workflow nodes."""

    lead_id: int

    status: NotRequired[str]

    activity_evidence: NotRequired[list[dict[str, object]]]

    tool_calls: NotRequired[int]

    errors: NotRequired[list[str]]

    intent_classification: NotRequired[dict[str, object]]

    route: NotRequired[str]
