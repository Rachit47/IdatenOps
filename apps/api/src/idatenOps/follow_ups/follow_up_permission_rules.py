"""Deterministic contact-permission checks for follow-up proposals.

This module decides whether a task type may be proposed. It does not send
messages, place calls, approve a proposal, or create a database record.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from idatenops.leads.lead_models import ContactPermission


class FollowUpTaskType(StrEnum):
    CALL = "call"
    PREPARE_MESSAGE_DRAFT = "prepare_message_draft"
    REVIEW_CONTACT_PERMISSION = "review_contact_permission"
    REVIEW_INVENTORY_ALTERNATIVE = "review_inventory_alternative"
    VERIFY_LEAD_DETAILS = "verify_lead_details"
    FOLLOW_UP_REVIEW = "follow_up_review"


class FollowUpPermissionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    reason_code: str
    reason: str


_INTERNAL_REVIEW_TASKS = {
    FollowUpTaskType.REVIEW_CONTACT_PERMISSION,
    FollowUpTaskType.REVIEW_INVENTORY_ALTERNATIVE,
    FollowUpTaskType.VERIFY_LEAD_DETAILS,
    FollowUpTaskType.FOLLOW_UP_REVIEW,
}
_OUTREACH_TASKS = {
    FollowUpTaskType.CALL,
    FollowUpTaskType.PREPARE_MESSAGE_DRAFT,
}


def evaluate_follow_up_permission(
    contact_permission: ContactPermission,
    task_type: FollowUpTaskType,
) -> FollowUpPermissionDecision:
    """Check whether a proposed task fits the current contact-permission state.

    Unknown permission allows only a permission-review task. A do-not-contact
    record blocks calls and message drafts but allows internal record review.
    """
    if contact_permission is ContactPermission.UNKNOWN:
        if task_type is FollowUpTaskType.REVIEW_CONTACT_PERMISSION:
            return FollowUpPermissionDecision(
                allowed=True,
                reason_code="permission_review_allowed",
                reason="Contact permission is unknown; staff may review and record it.",
            )
        return FollowUpPermissionDecision(
            allowed=False,
            reason_code="permission_unknown",
            reason="Unknown contact permission allows only a permission-review task.",
        )

    if contact_permission is ContactPermission.DO_NOT_CONTACT:
        if task_type in _OUTREACH_TASKS:
            return FollowUpPermissionDecision(
                allowed=False,
                reason_code="do_not_contact_blocks_outreach",
                reason="Do-not-contact status blocks calls and message drafts.",
            )
        if task_type in _INTERNAL_REVIEW_TASKS:
            return FollowUpPermissionDecision(
                allowed=True,
                reason_code="internal_review_allowed",
                reason="Internal record review is allowed; no customer contact is made.",
            )

    return FollowUpPermissionDecision(
        allowed=True,
        reason_code="contact_permission_permitted",
        reason="The recorded contact-permission state allows this task type.",
    )
