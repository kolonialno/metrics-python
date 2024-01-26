from typing import Callable

from django.http import HttpRequest, HttpResponse

from ._metrics import (
    VIEW_DUPLICATE_QUERY_COUNT,
    VIEW_QUERY_COUNT,
    VIEW_QUERY_DURATION,
    VIEW_QUERY_REQUESTS_COUNT,
)
from ._query_counter import QueryCounter
from ._utils import get_request_method, get_view_name


class QueryCountMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        with QueryCounter.create_as_current() as counter:
            response = self.get_response(request)

            method = get_request_method(request)
            view = get_view_name(request)
            status = str(response.status_code)

            labels = {"method": method, "view": view, "status": status}

            VIEW_QUERY_REQUESTS_COUNT.labels(**labels).inc()

            for (
                db,
                query_duration,
            ) in counter.get_total_query_duration_seconds_by_alias().items():
                VIEW_QUERY_DURATION.labels(db=db, **labels).observe(query_duration)

            for (
                db,
                query_count,
            ) in counter.get_total_query_count_by_alias().items():
                VIEW_QUERY_COUNT.labels(db=db, **labels).inc(query_count)

            for (
                db,
                query_count,
            ) in counter.get_total_duplicate_query_count_by_alias().items():
                VIEW_DUPLICATE_QUERY_COUNT.labels(db=db, **labels).inc(query_count)

            return response
