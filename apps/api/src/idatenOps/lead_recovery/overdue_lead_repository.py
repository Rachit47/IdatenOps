"""Read overdue leads from MySQL."""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from idatenops.lead_recovery.overdue_lead_models import (
    OverdueLeadSummary,
)


OVERDUE_LEADS_QUERY = text(
    """
    SELECT
        l.lead_id,
        l.lead_code,
        l.stage,
        l.location_id,
        l.next_follow_up_at AS next_follow_up_at_utc,

        p.display_name AS prospect_name,
        p.city AS prospect_city,
        p.contact_permission,

        l.assigned_team_member_id,
        tm.display_name AS assigned_salesperson_name

    FROM sales_leads AS l

    JOIN prospects AS p
        ON p.prospect_id = l.prospect_id

    LEFT JOIN team_members AS tm
        ON tm.team_member_id = l.assigned_team_member_id

    WHERE l.next_follow_up_at < :as_of_utc
      AND l.stage NOT IN ('won', 'lost', 'invalid')

    ORDER BY l.next_follow_up_at ASC, l.lead_id ASC
    LIMIT :limit
    """
)


def find_overdue_leads(
    session: Session,
    *,
    now_utc: datetime,
    limit: int = 50,
) -> list[OverdueLeadSummary]:
    """Return open leads whose follow-up time has passed."""

    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc must include a timezone")

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    # MySQL DATETIME has no timezone information.
    # Our application stores follow-up times as UTC.
    cutoff_utc = (
        now_utc.astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    rows = session.execute(
        OVERDUE_LEADS_QUERY,
        {
            "as_of_utc": cutoff_utc,
            "limit": limit,
        },
    ).mappings().all()

    overdue_leads: list[OverdueLeadSummary] = []

    for row in rows:
        lead_data = dict(row)

        # MySQL returns DATETIME as a datetime without a timezone.
        # Our database rule says this value represents UTC.
        due_time = lead_data["next_follow_up_at_utc"]

        if due_time.tzinfo is None:
            lead_data["next_follow_up_at_utc"] = due_time.replace(
                tzinfo=timezone.utc
            )
        else:
            lead_data["next_follow_up_at_utc"] = due_time.astimezone(
                timezone.utc
            )

        overdue_leads.append(
            OverdueLeadSummary.model_validate(lead_data)
        )

    return overdue_leads