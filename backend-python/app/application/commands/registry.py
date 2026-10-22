"""Commands declared once: what a command is called in the links, who may run it, and what it
does. The services keep one registry per command family next to themselves
(COMPONENT_COMMANDS, TOOL_COMMANDS) - dispatch (execute_command), permission checks
(ComponentPermissionValidator) and HATEOAS links (ComponentLinkBuilder) all loop over it, so
adding a command is one enum member plus one registry entry.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.domain.composite import lifecycle
from app.domain.models.component import Component
from app.domain.models.user import User

#: who may run a command on a component - the viewer is None when anonymous. Refused: 403
Allowed = Callable[[User | None, Component], bool]
#: whether the command applies to the component's current state - not a question of who
#: asks. Only decides whether its link is offered; the service refuses it with its own 409,
#: which says why (e.g. "published too long ago - deprecate it instead")
Available = Callable[[Component], bool]


def always(component: Component) -> bool:
    return True


@dataclass(frozen=True)
class CommandSpec[TService, TCommand]:
    #: the HATEOAS rel the command is offered under (e.g. "publish") - part of the API, the
    #: frontend looks for it
    rel: str
    allowed: Allowed
    #: (service, component, command, actor id) -> the component to respond with. Runs inside
    #: execute_command, which owns the transaction where the family has one
    run: Callable[[TService, Component, TCommand, uuid.UUID], Awaitable[Component]]
    available: Available = always


def is_logged_in(user: User | None, component: Component | None = None) -> bool:
    return user is not None


def is_owner(user: User | None, component: Component) -> bool:
    return user is not None and component.created_by_id == user.id


def unpublish_window() -> timedelta:
    """How long after its first publish a version may still go back to a draft (.env)."""
    return timedelta(seconds=get_settings().unpublish_window_seconds)


def within_unpublish_window_now(component: Component) -> bool:
    """For unpublish - only while the version is young enough to become a draft again; after
    that it can only be deprecated (see lifecycle.within_unpublish_window)."""
    return lifecycle.within_unpublish_window(component, datetime.now(UTC), unpublish_window())


def is_not_superseded(component: Component) -> bool:
    """For the commands that make a version PUBLISHED - not while a newer version of the
    lineage is published (see lifecycle.newer_published)."""
    return not component.is_superseded


def is_readable_by(user: User | None, component: Component) -> bool:
    """Public components (published or deprecated) are readable by everyone, drafts by their
    owner only."""
    return lifecycle.is_public(component) or is_owner(user, component)


def is_tool_owner(user: User | None, component: Component) -> bool:
    return component.is_tool and is_owner(user, component)


def is_packaged_tool_owner(user: User | None, component: Component) -> bool:
    return is_tool_owner(user, component) and component.is_packaged
