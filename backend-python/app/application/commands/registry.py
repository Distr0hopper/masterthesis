"""Commands declared once: what a command is called in the links, who may run it, and what it
does. The services keep one registry per command family next to themselves
(COMPONENT_COMMANDS, TOOL_COMMANDS) - dispatch (execute_command), permission checks
(ComponentPermissionValidator) and HATEOAS links (ComponentLinkBuilder) all loop over it, so
adding a command is one enum member plus one registry entry.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.domain.models.component import Component
from app.domain.models.user import User

#: who may run a command on a component - the viewer is None when anonymous
Allowed = Callable[[User | None, Component], bool]


@dataclass(frozen=True)
class CommandSpec[TService, TCommand]:
    #: the HATEOAS rel the command is offered under (e.g. "publish") - part of the API, the
    #: frontend looks for it
    rel: str
    allowed: Allowed
    #: (service, component, command, actor id) -> the component to respond with. Runs inside
    #: execute_command, which owns the transaction where the family has one
    run: Callable[[TService, Component, TCommand, uuid.UUID], Awaitable[Component]]


def is_logged_in(user: User | None, component: Component) -> bool:
    return user is not None


def is_owner(user: User | None, component: Component) -> bool:
    return user is not None and component.created_by_id == user.id


def is_tool_owner(user: User | None, component: Component) -> bool:
    return component.is_tool and is_owner(user, component)
