"""Who may open and change a builder canvas - only its creator, whatever they do with it."""

import uuid

from app.api.permission.workflow_draft_permission_validator import WorkflowDraftPermissionValidator
from app.domain.models.user import User
from app.domain.models.workflow_draft import WorkflowDraft

OWNER = User(id=uuid.uuid4(), email="owner@example.com")
STRANGER = User(id=uuid.uuid4(), email="stranger@example.com")


def draft() -> WorkflowDraft:
    return WorkflowDraft(id=uuid.uuid4(), name="canvas", canvas_state="{}", created_by_id=OWNER.id)


def test_the_owner_may_read_update_and_delete_their_draft() -> None:
    validator = WorkflowDraftPermissionValidator(OWNER)
    d = draft()

    assert validator.can_read(d)
    assert validator.can_update(d)
    assert validator.can_delete(d)


def test_nobody_else_may_touch_it() -> None:
    d = draft()
    for user in (STRANGER, None):
        validator = WorkflowDraftPermissionValidator(user)
        assert not validator.can_read(d)
        assert not validator.can_update(d)
        assert not validator.can_delete(d)


def test_any_logged_in_user_may_create_one() -> None:
    assert WorkflowDraftPermissionValidator(STRANGER).can_create()
    assert not WorkflowDraftPermissionValidator(None).can_create()
