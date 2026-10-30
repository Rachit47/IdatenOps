"""Shared state for Agent Savitar's investigation workflow."""

from typing import Literal, TypedDict


class SavitarState(TypedDict, total=False):
    """Data carried between workflow nodes."""

    lead_id: int
    status: Literal[
        "started",
        "investigating",
        "completed",
        "failed",
    ]
    activity_evidence: list[dict[str, object]]
    tool_calls: int
    errors: list[str]