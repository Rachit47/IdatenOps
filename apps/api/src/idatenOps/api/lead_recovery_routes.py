"""HTTP routes for lead recovery."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from idatenops.infrastructure.database import get_db_session
from idatenops.lead_recovery.overdue_lead_models import (
    OverdueLeadSummary,
)
from idatenops.lead_recovery.overdue_lead_service import (
    list_overdue_leads,
)


router = APIRouter(
    prefix="/api/v1/lead-recovery",
    tags=["Lead Recovery"],
)


@router.get(
    "/overdue",
    response_model=list[OverdueLeadSummary],
    summary="List overdue leads",
)
def get_overdue_leads(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> list[OverdueLeadSummary]:
    """Return leads that are overdue for follow-up."""

    return list_overdue_leads(
        session,
        limit=limit,
    )