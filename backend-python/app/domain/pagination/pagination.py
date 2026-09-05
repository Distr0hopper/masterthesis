from dataclasses import dataclass

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
DEFAULT_OFFSET = 0


@dataclass
class PaginatedList:
    """Pagination parameters for queries."""

    limit: int = DEFAULT_LIMIT
    offset: int = DEFAULT_OFFSET

    def __post_init__(self) -> None:
        """Validate and clamp values after initialization."""
        if self.limit < 1:
            self.limit = 1
        elif self.limit > MAX_LIMIT:
            self.limit = MAX_LIMIT

        if self.offset < 0:
            self.offset = 0
