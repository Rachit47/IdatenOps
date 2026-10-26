
"""Database queries for lead data."""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from idatenops.lead_recovery.overdue_lead_models import (
    OverdueLeadSummary,
)
from idatenops.leads.lead_models import LeadActivityEvidence


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

LEAD_ACTIVITY_HISTORY_QUERY = text(
    """
    SELECT
        lead_activity_id AS activity_id,
        lead_id,
        activity_type,
        direction,
        occurred_at AS occurred_at_utc
    FROM lead_activities
    WHERE lead_id = :lead_id
    ORDER BY occurred_at DESC, lead_activity_id DESC
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

    cutoff_utc = (
        now_utc.astimezone(timezone.utc).replace(tzinfo=None)
    )

    rows = session.execute(
        OVERDUE_LEADS_QUERY,
        {"as_of_utc": cutoff_utc, "limit": limit},
    ).mappings().all()

    results: list[OverdueLeadSummary] = []

    for row in rows:
        lead_data = dict(row)
        due_time = lead_data["next_follow_up_at_utc"]

        if due_time.tzinfo is None:
            lead_data["next_follow_up_at_utc"] = due_time.replace(
                tzinfo=timezone.utc
            )
        else:
            lead_data["next_follow_up_at_utc"] = due_time.astimezone(
                timezone.utc
            )

        results.append(OverdueLeadSummary.model_validate(lead_data))

    return results


def get_lead_activity_history(
    session: Session,
    *,
    lead_id: int,
    limit: int = 50,
) -> list[LeadActivityEvidence]:
    """Return recent activity evidence for one lead."""

    if lead_id <= 0:
        raise ValueError("lead_id must be positive")

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    rows = session.execute(
        LEAD_ACTIVITY_HISTORY_QUERY,
        {"lead_id": lead_id, "limit": limit},
    ).mappings().all()

    results: list[LeadActivityEvidence] = []

    for row in rows:
        activity_data = dict(row)
        occurred_at = activity_data["occurred_at_utc"]

        # The schema stores these DATETIME values as UTC.
        if occurred_at.tzinfo is None:
            activity_data["occurred_at_utc"] = occurred_at.replace(
                tzinfo=timezone.utc
            )
        else:
            activity_data["occurred_at_utc"] = occurred_at.astimezone(
                timezone.utc
            )

        results.append(
            LeadActivityEvidence.model_validate(activity_data)
        )

    return results
