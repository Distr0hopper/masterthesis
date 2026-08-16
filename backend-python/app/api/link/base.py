from abc import ABC, abstractmethod

from app.api.link.model import Link, LinkModel
from app.domain.models.user import User


class BaseLinkBuilder[TEntity, TDto: LinkModel, TValidator](ABC):
    def __init__(self, current_user: User | None) -> None:
        self.current_user = current_user
        self._validator = self._create_validator()

    @abstractmethod
    def _create_validator(self) -> TValidator: ...

    @abstractmethod
    def _get_available_links(self, entity: TEntity) -> dict[str, Link]: ...

    @abstractmethod
    def _is_link_allowed(self, rel: str, entity: TEntity) -> bool: ...

    def attach_links(self, dto: TDto, entity: TEntity) -> TDto:
        dto.links = self._filter_links(entity)
        return dto

    def _filter_links(self, entity: TEntity) -> dict[str, Link]:
        return {
            rel: link
            for rel, link in self._get_available_links(entity).items()
            if self._is_link_allowed(rel, entity)
        }
