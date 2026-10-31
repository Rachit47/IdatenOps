
"""Intent classification using recorded lead activity."""

from datetime import datetime

from idatenops.agent.models import (
    IntentClassification,
    LeadIntent,
)


def classify_activity_evidence(
    activity_evidence: list[dict[str, object]],
) -> IntentClassification:
    """Classify intent using the existing typed activity evidence."""

    if not activity_evidence:
        return IntentClassification(
            intent=LeadIntent.HUMAN_REVIEW,
            reason="No lead activity evidence is available.",
        )

    inbound_test_drive_events = []

    for activity in activity_evidence:
        if (
            activity.get("direction") == "inbound"
            and activity.get("activity_type")
            in {
                "test_drive_requested",
                "test_drive_request_withdrawn",
            }
        ):
            try:
                occurred_at = datetime.fromisoformat(
                    str(activity["occurred_at_utc"])
                )
                activity_id = int(activity["activity_id"])
            except (KeyError, TypeError, ValueError):
                return IntentClassification(
                    intent=LeadIntent.HUMAN_REVIEW,
                    reason="Activity evidence is incomplete.",
                )

            inbound_test_drive_events.append(
                (occurred_at, activity_id, activity["activity_type"])
            )

    if inbound_test_drive_events:
        latest_event = max(
            inbound_test_drive_events,
            key=lambda event: (event[0], event[1]),
        )

        _, activity_id, activity_type = latest_event

        if activity_type == "test_drive_requested":
            return IntentClassification(
                intent=LeadIntent.TEST_DRIVE,
                reason="The latest recorded test-drive event is an inbound request.",
                supporting_activity_ids=[activity_id],
            )

        return IntentClassification(
            intent=LeadIntent.FOLLOW_UP,
            reason="The buyer's latest recorded test-drive event is a withdrawal.",
            supporting_activity_ids=[activity_id],
        )

    latest_activity = max(
        activity_evidence,
        key=lambda activity: str(activity["occurred_at_utc"]),
    )

    try:
        activity_id = int(latest_activity["activity_id"])
    except (KeyError, TypeError, ValueError):
        return IntentClassification(
            intent=LeadIntent.HUMAN_REVIEW,
            reason="The latest activity evidence is incomplete.",
        )

    return IntentClassification(
        intent=LeadIntent.FOLLOW_UP,
        reason="Activity exists, but no active test-drive request is recorded.",
        supporting_activity_ids=[activity_id],
    )
