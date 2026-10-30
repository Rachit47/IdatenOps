"""LangGraph workflow for lead activity investigation."""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from idatenops.agent.state import SavitarState
from idatenops.agent.tools.lead_activity_tool import (
    LeadActivityHistoryInput,
    get_lead_activity_history_tool,
)

logger = logging.getLogger(__name__)


def create_activity_investigation_graph(session: Session):
    """Build a graph using the caller's database session."""

    def validate_request(state: SavitarState) -> dict[str, object]:
        """Reject invalid lead IDs before data access."""

        lead_id = state.get("lead_id")

        if (
            not isinstance(lead_id, int)
            or isinstance(lead_id, bool)
            or lead_id <= 0
        ):
            return {
                "status": "failed",
                "activity_evidence": [],
                "tool_calls": 0,
                "errors": ["invalid_lead_id"],
            }

        return {
            "status": "investigating",
            "activity_evidence": [],
            "tool_calls": 0,
            "errors": [],
        }

    def route_after_validation(
        state: SavitarState,
    ) -> Literal["load_activity_history", "finish"]:
        """Choose whether to fetch activity history or stop."""

        if state.get("status") == "failed":
            return "finish"

        return "load_activity_history"

    def load_activity_history(
        state: SavitarState,
    ) -> dict[str, object]:
        """Retrieve activity evidence through the existing tool."""

        lead_id = state["lead_id"]

        try:
            request = LeadActivityHistoryInput(lead_id=lead_id)

            activities = get_lead_activity_history_tool(
                session,
                request,
            )

            return {
                "status": "completed",
                "activity_evidence": [
                    activity.model_dump(mode="json")
                    for activity in activities
                ],
                "tool_calls": state.get("tool_calls", 0) + 1,
                "errors": [],
            }

        except Exception:
            # Return a safe error instead of raw database details.
            logger.warning(
                "Activity-history retrieval failed for lead_id=%s",
                lead_id,
            )

            return {
                "status": "failed",
                "activity_evidence": [],
                "tool_calls": state.get("tool_calls", 0) + 1,
                "errors": ["activity_history_retrieval_failed"],
            }

    builder = StateGraph(SavitarState)

    builder.add_node("validate_request", validate_request)
    builder.add_node("load_activity_history", load_activity_history)

    builder.add_edge(START, "validate_request")

    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {
            "load_activity_history": "load_activity_history",
            "finish": END,
        },
    )

    builder.add_edge("load_activity_history", END)

    return builder.compile()