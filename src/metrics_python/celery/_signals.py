import time
from datetime import datetime
from typing import Any

from django.utils import timezone

from ..generics.workers import export_worker_busy_state
from ._constants import PUBLISH_TIME_HEADER, TASK_HEADERS
from ._metrics import (
    TASK_EXECUTION_DELAY,
    TASK_EXECUTION_DURATION,
    TASK_LAST_EXECUTION,
    TASKS_EXECUTED,
)


def worker_process_init(**kwargs: Any) -> None:
    # Set the worker as idle on startup
    export_worker_busy_state(busy=False, worker_type="celery")


def before_task_publish(*args: Any, **kwargs: Any) -> None:
    # Add task publish time to the task headers.
    headers = {
        PUBLISH_TIME_HEADER: timezone.now().isoformat(),
    }

    # Update metrics-python headers
    task_headers = kwargs.get("headers") or {}
    task_headers.setdefault(TASK_HEADERS, {})
    task_headers[TASK_HEADERS].update(headers)
    kwargs["headers"] = task_headers


def task_prerun(task: Any, **kwargs: Any) -> None:
    queue: str = getattr(task, "queue", "default")
    headers: dict[str, Any] = task.request.get(TASK_HEADERS, {})

    # Set the worker as busy before we start to process a task
    export_worker_busy_state(busy=True, worker_type="celery")

    # Set the task execution delay
    task_published_time = headers.get(PUBLISH_TIME_HEADER)
    if task_published_time:
        try:
            now = timezone.now()
            task_published = datetime.fromisoformat(task_published_time)
            delay = (now - task_published).total_seconds()

            TASK_EXECUTION_DELAY.labels(task=task.name, queue=queue).observe(delay)
        except ValueError:
            pass

    # Set the task start time, this is used to measure the task
    # execution duration.
    task.__metrics_python_start_time = time.perf_counter()


def task_postrun(task: Any, **kwargs: Any) -> None:
    state: str = kwargs.get("state", "unknown")
    queue: str = getattr(task, "queue", "default")

    # Set the task execution duration
    task_started_time = getattr(task, "__metrics_python_start_time", None)
    if task_started_time:
        duration = time.perf_counter() - task_started_time
        TASK_EXECUTION_DURATION.labels(
            task=task.name, queue=queue, state=state
        ).observe(duration)

    # Set the worker as idle after the task is processed
    export_worker_busy_state(busy=False, worker_type="celery")

    # Bump the tasks executed counter
    TASKS_EXECUTED.labels(task=task.name, queue=queue, state=state).inc()

    # Update the last executed timestamp
    TASK_LAST_EXECUTION.labels(
        task=task.name, queue=queue, state=state
    ).set_to_current_time()
