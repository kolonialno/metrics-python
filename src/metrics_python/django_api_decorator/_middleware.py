import time
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

from ..django._utils import get_request_method, get_view_name
from ._metrics import VIEW_DURATION

API_DECORATOR_VIEW = "__metrics_python_django_api_decorator_view"


class DjangoAPIDecoratorMetricsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        view_start = time.perf_counter()

        response = self.get_response(request)

        if getattr(request, API_DECORATOR_VIEW, False):
            view_duration = time.perf_counter() - view_start

            method = get_request_method(request)
            view = get_view_name(request)
            status = str(response.status_code)

            VIEW_DURATION.labels(method=method, view=view, status=status).observe(
                view_duration
            )

        return response

    def process_view(
        self, request: HttpRequest, view_func: Any, view_args: Any, view_kwargs: Any
    ) -> None:
        """
        Set the __metrics_python_django_api_decorator_view flag on the request to
        indicate that this is a request to a view served by django-api-decorator.
        """
        api_meta = getattr(view_func, "_api_meta", None)
        if api_meta:
            setattr(request, API_DECORATOR_VIEW, True)
