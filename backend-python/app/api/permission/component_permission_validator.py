from app.domain.models.component import Component
from app.domain.models.user import User


class ComponentPermissionValidator:
    def __init__(self, user: User) -> None:
        self.user = user

    def can_create(self) -> bool:
        return True

    def can_update(self, component: Component) -> bool:
        return component.created_by_id == self.user.id

    def can_delete(self, component: Component) -> bool:
        return component.created_by_id == self.user.id