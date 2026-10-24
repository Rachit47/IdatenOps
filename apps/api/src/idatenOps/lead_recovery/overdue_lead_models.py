"""Data returned by the overdue-lead feature."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from idatenops.leads.lead_models import ContactPermission


class OverdueLeadSummary(BaseModel):
    """Small summary shown in the overdue-lead list."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lead_id: int = Field(gt=0)
    lead_code: str
    stage: str
    location_id: int = Field(gt=0)

    prospect_name: str
    prospect_city: str
    contact_permission: ContactPermission

    next_follow_up_at_utc: datetime

    assigned_team_member_id: int | None
    assigned_salesperson_name: str | None