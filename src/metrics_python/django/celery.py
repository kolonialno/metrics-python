from functools import wraps
from typing import TYPE_CHECKING, Any

from celery.app.trace import task_has_custom

from ._metrics import (
    CELERY_DUPLICATE_QUERY_COUNT,
    CELERY_QUERY_COUNT,
    CELERY_QUERY_DURATION,
    CELERY_QUERY_REQUESTS_COUNT,
)

if TYPE_CHECKING:
    from ._query_counter import QueryCounter


def setup_celery_database_metrics() -> None:
    """
    Patch celery to export database metrics.
    """

    import celery.app.trace as trace  # noqa

    if hasattr(trace, "_metrics_python_is_patched"):
        return

    old_build_tracer = trace.build_tracer

    def metrics_python_build_tracer(
        name: str, task: Any, *args: Any, **kwargs: Any
    ) -> Any:
        if not getattr(task, "_metrics_python_is_patched", False):
            # Determine whether Celery will use __call__ or run and patch
            # accordingly
            if task_has_custom(task, "__call__"):
                type(task).__call__ = _wrap_task_call(task, type(task).__call__)
            else:
                task.run = _wrap_task_call(task, task.run)

            # `build_tracer` is apparently called for every task
            # invocation. Can't wrap every celery task for every invocation
            # or we will get infinitely nested wrapper functions.
            task._metrics_python_is_patched = True

        return old_build_tracer(name, task, *args, **kwargs)

    trace.build_tracer = metrics_python_build_tracer
    trace._metrics_python_is_patched = True


def _measure_task(*, task: Any, counter: "QueryCounter") -> None:
    labels = {"task": task.name}

    CELERY_QUERY_REQUESTS_COUNT.labels(**labels).inc()

    for (
        db,
        query_duration,
    ) in counter.get_total_query_duration_seconds_by_alias().items():
        CELERY_QUERY_DURATION.labels(db=db, **labels).observe(query_duration)

    for (
        db,
        query_count,
    ) in counter.get_total_query_count_by_alias().items():
        CELERY_QUERY_COUNT.labels(db=db, **labels).inc(query_count)

    for (
        db,
        query_count,
    ) in counter.get_total_duplicate_query_count_by_alias().items():
        CELERY_DUPLICATE_QUERY_COUNT.labels(db=db, **labels).inc(query_count)


def _wrap_task_call(task: Any, f: Any) -> Any:
    @wraps(f)
    def _inner(*args: Any, **kwargs: Any) -> Any:
        # We don't enable the query counter if Celery is running in eager mode,
        # the request middleware is most likely in place already.
        if getattr(task.request, "is_eager", False):
            return f(*args, **kwargs)

        from ._query_counter import QueryCounter

        # Initialize the query counter and measure the result after the task
        # is complete.
        with QueryCounter.create_counter() as counter:
            result = f(*args, **kwargs)
            _measure_task(task=task, counter=counter)
            return result

    return _inner
