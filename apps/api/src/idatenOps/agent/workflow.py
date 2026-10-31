
"""LangGraph workflow for lead activity investigation."""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from idatenops.agent.classification import (
    classify_activity_evidence,
)
from idatenops.agent.state import SavitarState
from idatenops.agent.tools.lead_activity_tool import (
    LeadActivityHistoryInput,
    get_lead_activity_history_tool,
)

logger = logging.getLogger(__name__)


def create_activity_investigation_graph(session: Session):
    """Build the lead investigation and classification graph."""

    def validate_request(state: SavitarState) -> dict[str, object]:
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
        if state.get("status") == "failed":
            return "finish"

        return "load_activity_history"

    def load_activity_history(
        state: SavitarState,
    ) -> dict[str, object]:
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

    def classify_intent(
        state: SavitarState,
    ) -> dict[str, object]:
        classification = classify_activity_evidence(
            state.get("activity_evidence", [])
        )

        return {
            "intent_classification": classification.model_dump(
                mode="json"
            )
        }

    def route_by_intent(
        state: SavitarState,
    ) -> Literal[
        "test_drive",
        "follow_up",
        "human_review",
        "finish",
    ]:
        if state.get("status") == "failed":
            return "finish"

        classification = state.get("intent_classification")

        if not classification:
            return "human_review"

        intent = classification.get("intent")

        if intent == "test_drive":
            return "test_drive"

        if intent == "follow_up":
            return "follow_up"

        return "human_review"

    builder = StateGraph(SavitarState)

    builder.add_node("validate_request", validate_request)
    builder.add_node("load_activity_history", load_activity_history)
    builder.add_node("classify_intent", classify_intent)

    builder.add_edge(START, "validate_request")

    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {
            "load_activity_history": "load_activity_history",
            "finish": END,
        },
    )

    builder.add_conditional_edges(
        "load_activity_history",
        lambda state: (
            "classify" if state.get("status") == "completed"
            else "finish"
        ),
        {
            "classify": "classify_intent",
            "finish": END,
        },
    )

    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "test_drive": END,
            "follow_up": END,
            "human_review": END,
            "finish": END,
        },
    )

    return builder.compile()
