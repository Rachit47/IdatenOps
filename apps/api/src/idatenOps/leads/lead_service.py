
"""Application operations for lead data."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from idatenops.leads.lead_models import LeadActivityEvidence
from idatenops.leads.lead_repository import (
    find_overdue_leads,
    get_lead_activity_history as fetch_lead_activity_history,
)
from idatenops.lead_recovery.overdue_lead_models import (
    OverdueLeadSummary,
)


def list_overdue_leads(
    session: Session,
    *,
    limit: int = 50,
    now_utc: datetime | None = None,
) -> list[OverdueLeadSummary]:
    """List leads whose follow-up time has passed."""

    check_time = (
        now_utc
        if now_utc is not None
        else datetime.now(timezone.utc)
    )

    return find_overdue_leads(
        session,
        now_utc=check_time,
        limit=limit,
    )


def get_lead_activity_history(
    session: Session,
    *,
    lead_id: int,
    limit: int = 50,
) -> list[LeadActivityEvidence]:
    """Get recent activity evidence for a lead."""

    return fetch_lead_activity_history(
        session,
        lead_id=lead_id,
        limit=limit,
    )
