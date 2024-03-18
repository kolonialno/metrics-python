import time
from datetime import datetime
from typing import Any

from django.utils import timezone

from metrics_python.generics.heartbeats import HeartbeatState, capture_checkin

from ..generics.workers import export_worker_busy_state
from ._constants import BEAT_TASK_HEADER, TASK_HEADERS, TASK_PUBLISH_TIME_HEADER
from ._metrics import (
    TASK_EXECUTION_DELAY,
    TASK_EXECUTION_DURATION,
    TASK_LAST_EXECUTION,
)


def _get_headers(task: Any) -> dict[str, Any]:
    """
    Combine all headers in a celery task.
    """

    headers = task.request.get("headers") or {}

    # flatten nested headers
    if "headers" in headers:
        headers.update(headers["headers"])
        del headers["headers"]

    headers.update(task.request.get("properties") or {})

    return headers


def _set_headers(
    *, existing_headers: dict[str, Any], headers: dict[str, Any]
) -> dict[str, Any]:
    """
    Set metrics-python headers.
    """

    # Add metrics-python headers if not set.
    existing_headers.setdefault(TASK_HEADERS, {})

    # Add headers to the metrics-python header section.
    existing_headers[TASK_HEADERS].update(headers)

    return existing_headers


def worker_process_init(**kwargs: Any) -> None:
    # Set the worker as idle on startup
    export_worker_busy_state(busy=False, worker_type="celery")


def before_task_publish(*args: Any, **kwargs: Any) -> None:
    message_headers = kwargs.pop("headers", {})

    # Store metrics-python headers in the task headers, not the
    # message headers.
    message_headers.setdefault("headers", {})
    message_headers["headers"] = _set_headers(
        existing_headers=message_headers["headers"],
        headers={
            TASK_PUBLISH_TIME_HEADER: timezone.now().isoformat(),
        },
    )

    kwargs["headers"] = message_headers


def task_prerun(sender: Any, **kwargs: Any) -> None:
    headers = _get_headers(sender)
    metrics_python_headers = headers.get(TASK_HEADERS, {})

    queue: str = getattr(sender, "queue", "default")

    # Set the worker as busy before we start to process a task
    export_worker_busy_state(busy=True, worker_type="celery")

    # Set the task execution delay
    task_published_time = metrics_python_headers.get(TASK_PUBLISH_TIME_HEADER)
    if task_published_time:
        try:
            now = timezone.now()
            task_published = datetime.fromisoformat(task_published_time)
            delay = (now - task_published).total_seconds()

            TASK_EXECUTION_DELAY.labels(task=sender.name, queue=queue).observe(delay)
        except ValueError:
            pass

    # Set the task start time, this is used to measure the task
    # execution duration.
    sender.__metrics_python_start_time = time.perf_counter()


def task_postrun(sender: Any, **kwargs: Any) -> None:
    state: str = kwargs.get("state", "unknown")
    queue: str = getattr(sender, "queue", "default")

    # Set the task execution duration
    task_started_time = getattr(sender, "__metrics_python_start_time", None)
    if task_started_time:
        duration = time.perf_counter() - task_started_time
        TASK_EXECUTION_DURATION.labels(
            task=sender.name, queue=queue, state=state
        ).observe(duration)

    # Set the worker as idle after the task is processed
    export_worker_busy_state(busy=False, worker_type="celery")

    # Update the last executed timestamp
    TASK_LAST_EXECUTION.labels(
        task=sender.name, queue=queue, state=state
    ).set_to_current_time()


#
# Heartbeats
#


def crons_task_success(sender: Any, **kwargs: Any) -> None:
    headers = _get_headers(sender)
    metrics_python_headers = headers.get(TASK_HEADERS, {})
    if not metrics_python_headers.get(BEAT_TASK_HEADER, False):
        return

    # Set the task execution duration
    task_started_time = getattr(sender, "__metrics_python_start_time", None)

    duration: float | None = None
    if task_started_time:
        duration = time.perf_counter() - task_started_time

    capture_checkin(
        name=sender.name, state=HeartbeatState.OK, duration_seconds=duration
    )


def crons_task_failure(sender: Any, **kwargs: Any) -> None:
    headers = _get_headers(sender)
    metrics_python_headers = headers.get(TASK_HEADERS, {})
    if not metrics_python_headers.get(BEAT_TASK_HEADER, False):
        return

    # Set the task execution duration
    task_started_time = getattr(sender, "__metrics_python_start_time", None)

    duration: float | None = None
    if task_started_time:
        duration = time.perf_counter() - task_started_time

    capture_checkin(
        name=sender.name, state=HeartbeatState.ERROR, duration_seconds=duration
    )


def crons_task_retry(sender: Any, **kwargs: Any) -> None:
    headers = _get_headers(sender)
    metrics_python_headers = headers.get(TASK_HEADERS, {})
    if not metrics_python_headers.get(BEAT_TASK_HEADER, False):
        return

    # Set the task execution duration
    task_started_time = getattr(sender, "__metrics_python_start_time", None)

    duration: float | None = None
    if task_started_time:
        duration = time.perf_counter() - task_started_time

    capture_checkin(
        name=sender.name, state=HeartbeatState.ERROR, duration_seconds=duration
    )
