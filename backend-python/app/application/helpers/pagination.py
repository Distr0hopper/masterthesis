class PaginationHelper:
    """Turns a total row count into the page count a response DTO reports."""

    @staticmethod
    def total_pages(total: int, limit: int) -> int:
        """Number of pages a result set fills; 0 for an empty one."""
        if total <= 0 or limit <= 0:
            return 0
        return (total + limit - 1) // limit
