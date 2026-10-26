
"""Typed agent tool for retrieving lead activity history."""

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from idatenops.leads.lead_models import LeadActivityEvidence
from idatenops.leads.lead_service import get_lead_activity_history


class LeadActivityHistoryInput(BaseModel):
    """Validated input for the lead activity history tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lead_id: int = Field(gt=0, description="ID of the lead to investigate")
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of recent activities to retrieve",
    )


def get_lead_activity_history_tool(
    session: Session,
    request: LeadActivityHistoryInput,
) -> list[LeadActivityEvidence]:
    """Retrieve recent activity evidence for a lead.

    The shared lead service handles the application operation.
    The repository handles SQL and database row mapping.
    """

    return get_lead_activity_history(
        session,
        lead_id=request.lead_id,
        limit=request.limit,
    )
