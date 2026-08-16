from abc import ABC, abstractmethod

from app.domain.models.user import User


class PermissionValidator[TEntity](ABC):
    def __init__(self, user: User | None) -> None:
        self.user = user

    @abstractmethod
    def can_create(self) -> bool: ...

    @abstractmethod
    def can_update(self, entity: TEntity) -> bool: ...

    @abstractmethod
    def can_delete(self, entity: TEntity) -> bool: ...
