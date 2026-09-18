from app.api.permission.base import PermissionValidator
from app.application.commands.commands import ComponentCommandType
from app.domain.models.component import Component, ComponentStatus
from app.domain.models.user import User


class ComponentPermissionValidator(PermissionValidator[Component]):
    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, component: Component) -> bool:
        """Mirrors ComponentsService.get_visible_component: published components are public, drafts are owner-only."""
        if component.status == ComponentStatus.PUBLISHED:
            return True
        return self.user is not None and component.created_by_id == self.user.id

    def can_update(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_delete(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_favorite(self) -> bool:
        return self.user is not None

    def can_execute(self, component: Component, action: str | ComponentCommandType) -> bool:
        try:
            command = ComponentCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case ComponentCommandType.ADD_FAVORITE | ComponentCommandType.REMOVE_FAVORITE:
                return self.can_favorite()
            case ComponentCommandType.REPACKAGE:
                return self.can_update(component)
            case ComponentCommandType.PUBLISH:
                return self.can_update(component)
            case _:
                return False
