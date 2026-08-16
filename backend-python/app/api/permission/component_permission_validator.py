from app.api.permission.base import PermissionValidator
from app.domain.models.component import Component
from app.domain.models.user import User


class ComponentPermissionValidator(PermissionValidator[Component]):
    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, _component: Component) -> bool:
        """Components are public resources, readable by anyone including anonymous users."""
        return True

    def can_update(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_delete(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_favorite(self) -> bool:
        return self.user is not None
