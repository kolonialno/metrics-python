import asyncio
import contextlib
import time
from contextvars import ContextVar
from functools import wraps
from logging import getLogger
from typing import Any, Callable, Coroutine, Generator, Optional, cast

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import sync_and_async_middleware

from ._metrics import (
    MIDDLEWARE_DURATION,
    VIEW_DUPLICATE_QUERY_COUNT,
    VIEW_QUERY_COUNT,
    VIEW_QUERY_DURATION,
    VIEW_QUERY_REQUESTS_COUNT,
)
from ._query_counter import QueryCounter
from ._utils import get_request_method, get_view_name

logger = getLogger(__name__)

MIDDLEWARE = Callable[[HttpRequest], HttpResponse]
ASYNC_MIDDLEWARE = Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]]

_import_string_should_wrap_middleware: ContextVar[bool] = ContextVar(
    "import_string_should_wrap_middleware"
)


#
# Request query counter
#


def _measure_request(
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
            with QueryCounter.create_counter() as counter:
                response = await cast(ASYNC_MIDDLEWARE, get_response)(request)
                _measure_request(request=request, response=response, counter=counter)

                return response

        return async_middleware

    def middleware(request: HttpRequest) -> HttpResponse:
        with QueryCounter.create_counter() as counter:
            response = cast(MIDDLEWARE, get_response)(request)
            _measure_request(request=request, response=response, counter=counter)

            return response

    return middleware


#
# Middleware observability
#


def patch_middlewares() -> None:
    from django.core.handlers import base

    if hasattr(base, "_metrics_python_is_patched"):
        return

    old_import_string = base.import_string

    def metrics_python_patched_import_string(dotted_path: str) -> Any:
        rv = old_import_string(dotted_path)

        if _import_string_should_wrap_middleware.get(None):
            rv = _wrap_middleware(rv, dotted_path)

        return rv

    base.import_string = metrics_python_patched_import_string

    old_load_middleware = base.BaseHandler.load_middleware

    def metrics_python_patched_load_middleware(*args: Any, **kwargs: Any) -> Any:
        _import_string_should_wrap_middleware.set(True)
        try:
            return old_load_middleware(*args, **kwargs)
        finally:
            _import_string_should_wrap_middleware.set(False)

    base.BaseHandler.load_middleware = metrics_python_patched_load_middleware
    base._metrics_python_is_patched = True


def _wrap_middleware(middleware: Any, middleware_name: str) -> Any:  # noqa
    def _middleware_method(old_method: Any) -> str:
        """
        Return middleware method.
        """

        function_basename = getattr(old_method, "__name__", None)
        if not function_basename:
            return "<unnamed method>"

        return str(function_basename)

    @contextlib.contextmanager
    def _middleware_timer(
        old_method: Any,
        middleware: Optional["MetricsPythonWrappingMiddleware"] = None,
    ) -> Generator[None, None, None]:
        """
        Return a generator that is used to measure the method execution duration.
        """

        method_name = _middleware_method(old_method)

        start = time.perf_counter()

        yield

        duration = time.perf_counter() - start

        if middleware:
            get_response_duration = getattr(
                middleware, "_metric_python_get_response_duration", None
            )
            if not get_response_duration:
                logger.warning(
                    "Middleware was provided, but no get_response duration was found."
                )
            else:
                duration = max(duration - get_response_duration, 0)

            middleware._metric_python_get_response_duration = None

        MIDDLEWARE_DURATION.labels(
            middleware=middleware_name, method=method_name
        ).observe(duration)

    def _get_wrapped_method(old_method: Any) -> Any:
        """
        Wrap decorator method to mesure execution duration.
        """

        def metrics_python_wrapped_method(*args: Any, **kwargs: Any) -> Any:
            with _middleware_timer(old_method=old_method):
                return old_method(*args, **kwargs)

        wrapped_method = wraps(old_method)(metrics_python_wrapped_method)
        # Django compat.
        wrapped_method.__self__ = old_method.__self__  # type: ignore

        return wrapped_method

    def _get_wrapped_get_response(
        get_response: Any, middleware: "MetricsPythonWrappingMiddleware"
    ) -> Any:
        """
        We need to wrap get_response to subtract the time used by other
        middlewares and the view to get the time actually spent in the
        current middleware.
        """

        @contextlib.contextmanager
        def _get_response_timer() -> Generator[None, None, None]:
            start = time.perf_counter()

            yield

            middleware._metric_python_get_response_duration = (
                time.perf_counter() - start
            )

        def _get_response(*args: Any, **kwargs: Any) -> Any:
            with _get_response_timer():
                return get_response(*args, **kwargs)

        async def _aget_response(*args: Any, **kwargs: Any) -> Any:
            with _get_response_timer():
                return await get_response(*args, **kwargs)

        if asyncio.iscoroutinefunction(get_response):
            return wraps(get_response)(_aget_response)

        return wraps(get_response)(_get_response)

    class MetricsPythonWrappingMiddleware:
        async_capable = getattr(middleware, "async_capable", False)

        def __init__(self, get_response: Any = None, *args: Any, **kwargs: Any) -> None:
            if get_response:
                self._inner = middleware(
                    _get_wrapped_get_response(get_response, self), *args, **kwargs
                )
            else:
                self._inner = middleware(*args, **kwargs)

            # Used to identify if this is an async middleware or not.
            self.get_response = get_response

            self._call_method = None
            self._acall_method = None
            self._metric_python_get_response_duration: float | None = None

            if self.async_capable:
                self._async_check()

        def _async_check(self) -> None:
            if asyncio.iscoroutinefunction(self.get_response):
                self._is_coroutine = asyncio.coroutines._is_coroutine  # type: ignore

        def async_route_check(self) -> bool:
            return asyncio.iscoroutinefunction(self.get_response)

        def __getattr__(self, method_name: str) -> Any:
            if method_name not in (
                "process_request",
                "process_view",
                "process_template_response",
                "process_response",
                "process_exception",
            ):
                raise AttributeError()

            old_method = getattr(self._inner, method_name)
            rv = _get_wrapped_method(old_method)
            self.__dict__[method_name] = rv
            return rv

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            if self.async_route_check():
                return self.__acall__(*args, **kwargs)

            f = self._call_method
            if f is None:
                self._call_method = f = self._inner.__call__

            with _middleware_timer(old_method=f, middleware=self):
                return f(*args, **kwargs)

        async def __acall__(self, *args: Any, **kwargs: Any) -> Any:
            f = self._acall_method
            if f is None:
                if hasattr(self._inner, "__acall__"):
                    self._acall_method = f = self._inner.__acall__
                else:
                    self._acall_method = f = self._inner

            with _middleware_timer(old_method=f, middleware=self):
                return await f(*args, **kwargs)

    for attr in (
        "__name__",
        "__module__",
        "__qualname__",
    ):
        if hasattr(middleware, attr):
            setattr(MetricsPythonWrappingMiddleware, attr, getattr(middleware, attr))

    return MetricsPythonWrappingMiddleware
