"""Standard page-number pagination for FMMS REST APIs."""

from rest_framework.pagination import PageNumberPagination


class FMMSPageNumberPagination(PageNumberPagination):
    """Page-number pagination with a bounded page size.

    Attributes:
        page_size: Default number of results per page.
        page_size_query_param: Query parameter clients may use to override size.
        max_page_size: Hard upper bound for ``page_size``.
    """

    page_size: int = 20
    page_size_query_param: str = "page_size"
    max_page_size: int = 100
