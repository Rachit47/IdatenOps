import pytest

from idatenops.follow_ups.rules import (
    FollowUpTaskType,
    evaluate_follow_up_permission,
)
from idatenops.leads.types import ContactPermission


@pytest.mark.parametrize(
    "task_type",
    [FollowUpTaskType.CALL, FollowUpTaskType.PREPARE_MESSAGE_DRAFT],
)
def test_unknown_permission_blocks_outreach_tasks(task_type) -> None:
    decision = evaluate_follow_up_permission(ContactPermission.UNKNOWN, task_type)
    assert decision.allowed is False
    assert decision.reason_code == "permission_unknown"


def test_unknown_permission_allows_only_permission_review() -> None:
    decision = evaluate_follow_up_permission(
        ContactPermission.UNKNOWN,
        FollowUpTaskType.REVIEW_CONTACT_PERMISSION,
    )
    assert decision.allowed is True


@pytest.mark.parametrize(
    "task_type",
    [FollowUpTaskType.CALL, FollowUpTaskType.PREPARE_MESSAGE_DRAFT],
)
def test_do_not_contact_blocks_call_and_message_draft(task_type) -> None:
    decision = evaluate_follow_up_permission(
        ContactPermission.DO_NOT_CONTACT,
        task_type,
    )
    assert decision.allowed is False
    assert decision.reason_code == "do_not_contact_blocks_outreach"


@pytest.mark.parametrize(
    "task_type",
    [
        FollowUpTaskType.REVIEW_CONTACT_PERMISSION,
        FollowUpTaskType.REVIEW_INVENTORY_ALTERNATIVE,
        FollowUpTaskType.VERIFY_LEAD_DETAILS,
        FollowUpTaskType.FOLLOW_UP_REVIEW,
    ],
)
def test_do_not_contact_allows_internal_record_review(task_type) -> None:
    decision = evaluate_follow_up_permission(
        ContactPermission.DO_NOT_CONTACT,
        task_type,
    )
    assert decision.allowed is True


def test_permitted_contact_allows_a_call_task() -> None:
    decision = evaluate_follow_up_permission(
        ContactPermission.PERMITTED,
        FollowUpTaskType.CALL,
    )
    assert decision.allowed is True
