from app.api.dto.base import CamelModel
from app.api.dto.pagination import PaginatedResponseDtoV1, build_paginated_response
from app.domain.pagination.pagination import PaginatedList


class ErrorResponse(CamelModel):
    detail: str


class MyItemsResponseDtoV1[T](CamelModel):
    """The "my components" response shape of GET /components/mine.

    Independently paginated buckets, one per status, rather than one list the client
    splits: a single page of mixed-status rows can't be split into correct sections once
    pagination is involved.
    """

    published: PaginatedResponseDtoV1[T]
    unpublished: PaginatedResponseDtoV1[T]
    deprecated: PaginatedResponseDtoV1[T]


def build_my_items_response[T](
    published: tuple[list[T], int],
    published_pagination: PaginatedList,
    unpublished: tuple[list[T], int],
    unpublished_pagination: PaginatedList,
    deprecated: tuple[list[T], int],
    deprecated_pagination: PaginatedList,
) -> MyItemsResponseDtoV1[T]:
    return MyItemsResponseDtoV1[T](
        published=build_paginated_response(*published, published_pagination),
        unpublished=build_paginated_response(*unpublished, unpublished_pagination),
        deprecated=build_paginated_response(*deprecated, deprecated_pagination),
    )
