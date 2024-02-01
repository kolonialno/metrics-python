import asyncio
from typing import Any, Callable, Coroutine, cast

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import sync_and_async_middleware

from ._metrics import (
    VIEW_DUPLICATE_QUERY_COUNT,
    VIEW_QUERY_COUNT,
    VIEW_QUERY_DURATION,
    VIEW_QUERY_REQUESTS_COUNT,
)
from ._query_counter import QueryCounter
from ._utils import get_request_method, get_view_name

MIDDLEWARE = Callable[[HttpRequest], HttpResponse]
ASYNC_MIDDLEWARE = Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]]


def measure_request(
    *, request: HttpRequest, response: HttpResponse, counter: QueryCounter
) -> None:
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


@sync_and_async_middleware  # type: ignore
def QueryCountMiddleware(
    get_response: MIDDLEWARE | ASYNC_MIDDLEWARE,
) -> MIDDLEWARE | ASYNC_MIDDLEWARE:
    if asyncio.iscoroutinefunction(get_response):

        async def async_middleware(request: HttpRequest) -> HttpResponse:
            with QueryCounter.create_as_current() as counter:
                response = await cast(ASYNC_MIDDLEWARE, get_response)(request)
                measure_request(request=request, response=response, counter=counter)

                return response

        return async_middleware

    def middleware(request: HttpRequest) -> HttpResponse:
        with QueryCounter.create_as_current() as counter:
            response = cast(MIDDLEWARE, get_response)(request)
            measure_request(request=request, response=response, counter=counter)

            return response

    return middleware
