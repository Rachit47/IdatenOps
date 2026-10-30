"""Tests for Agent Savitar's investigation workflow."""

from unittest.mock import Mock

from idatenops.agent.workflow import (
    create_activity_investigation_graph,
)
from idatenops.leads.lead_models import (
    ActivityDirection,
    ActivityType,
    LeadActivityEvidence,
)


def test_workflow_returns_activity_evidence() -> None:
    session = Mock()

    activity = LeadActivityEvidence(
        activity_id=901,
        lead_id=101,
        activity_type=ActivityType.TEST_DRIVE_REQUESTED,
        direction=ActivityDirection.INBOUND,
        occurred_at_utc="2026-10-25T10:30:00+00:00",
    )

    graph = create_activity_investigation_graph(session)

    # Replace the real tool with a predictable test result.
    from idatenops.agent import workflow

    tool = Mock(return_value=[activity])
    original_tool = workflow.get_lead_activity_history_tool

    try:
        workflow.get_lead_activity_history_tool = tool

        result = graph.invoke({"lead_id": 101})

        assert result["status"] == "completed"
        assert result["tool_calls"] == 1
        assert result["errors"] == []
        assert result["activity_evidence"][0]["activity_id"] == 901
        tool.assert_called_once()

    finally:
        workflow.get_lead_activity_history_tool = original_tool


def test_workflow_stops_for_invalid_lead_id() -> None:
    session = Mock()
    graph = create_activity_investigation_graph(session)

    result = graph.invoke({"lead_id": -1})

    assert result["status"] == "failed"
    assert result["errors"] == ["invalid_lead_id"]
    assert result["tool_calls"] == 0


def test_workflow_returns_safe_error_on_tool_failure() -> None:
    session = Mock()
    graph = create_activity_investigation_graph(session)

    from idatenops.agent import workflow

    tool = Mock(side_effect=RuntimeError("private database detail"))
    original_tool = workflow.get_lead_activity_history_tool

    try:
        workflow.get_lead_activity_history_tool = tool

        result = graph.invoke({"lead_id": 101})

        assert result["status"] == "failed"
        assert result["errors"] == [
            "activity_history_retrieval_failed"
        ]
        assert "private database detail" not in str(result)

    finally:
        workflow.get_lead_activity_history_tool = original_tool