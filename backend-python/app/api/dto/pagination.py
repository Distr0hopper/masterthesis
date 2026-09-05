from typing import Annotated

from fastapi import Query

from app.api.dto.base import CamelModel
from app.application.helpers.pagination import PaginationHelper
from app.domain.pagination.pagination import DEFAULT_LIMIT, DEFAULT_OFFSET, MAX_LIMIT, PaginatedList


class ListQueryPaginationDtoV1:
    """FastAPI dependency: parses and validates `?limit=&offset=`.

    Used as `Annotated[ListQueryPaginationDtoV1, Depends()]` in a router - FastAPI
    builds one instance per request from the query string, `to_domain()` then hands
    the framework-free `PaginatedList` to the service/repository layers.
    """

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
        offset: Annotated[int, Query(ge=0)] = DEFAULT_OFFSET,
    ) -> None:
        self.limit = limit
        self.offset = offset

    def to_domain(self) -> PaginatedList:
        return PaginatedList(limit=self.limit, offset=self.offset)


class PaginatedResponseDtoV1[T](CamelModel):
    content: list[T]
    limit: int
    offset: int
    total_pages: int
    total_elements: int


def build_paginated_response[T](items: list[T], total: int, pagination: PaginatedList) -> PaginatedResponseDtoV1[T]:
    return PaginatedResponseDtoV1[T](
        content=items,
        limit=pagination.limit,
        offset=pagination.offset,
        total_pages=PaginationHelper.total_pages(total, pagination.limit),
        total_elements=total,
    )
