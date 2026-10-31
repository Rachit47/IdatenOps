
"""Validation helpers for Agent Savitar intent classification."""

from idatenops.agent.models import IntentClassification


def validate_classification_evidence(
    classification: IntentClassification,
    activity_evidence: list[dict[str, object]],
) -> bool:
    """Ensure cited activity IDs belong to the supplied evidence."""

    available_ids = {
        activity.get("activity_id")
        for activity in activity_evidence
    }

    if not classification.supporting_activity_ids:
        return False

    return all(
        activity_id in available_ids
        for activity_id in classification.supporting_activity_ids
    )
