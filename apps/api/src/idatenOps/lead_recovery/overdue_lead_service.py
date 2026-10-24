"""Business operations for lead recovery."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from idatenops.lead_recovery.overdue_lead_models import (
    OverdueLeadSummary,
)
from idatenops.lead_recovery.overdue_lead_repository import (
    find_overdue_leads,
)


def list_overdue_leads(
    session: Session,
    *,
    limit: int = 50,
    now_utc: datetime | None = None,
) -> list[OverdueLeadSummary]:
    """List overdue leads as of the supplied time or the current time."""

    check_time = (
        now_utc if now_utc is not None
        else datetime.now(timezone.utc)
    )

    return find_overdue_leads(
        session,
        now_utc=check_time,
        limit=limit,
    )