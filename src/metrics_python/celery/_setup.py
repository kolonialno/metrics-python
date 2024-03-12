import logging
from typing import Any

import celery
from celery.schedules import schedule as periodic_schedule

from metrics_python.generics.heartbeats import (
    HeartbeatState,
    capture_checkin,
    register_heartbeat,
)

from ._signals import (
    before_task_publish,
    crons_task_failure,
    crons_task_retry,
    crons_task_success,
    task_postrun,
    task_prerun,
    worker_process_init,
)

logger = logging.getLogger(__name__)


def setup_celery_metrics(patch_beat: bool = False) -> None:
    """
    Patch celery to export metrics.
    """

    # Celery signals has logic to prevent duplicate signal handlers,
    # but we keep the patched logic here to prevent issues in the
    # future if we decide to patch additional celery methods.
    if hasattr(celery, "_metrics_python_is_patched"):
        return

    if patch_beat:
        _patch_beat()
        _register_beat_heartbeats()
        celery.signals.task_success.connect(crons_task_success, weak=True)
        celery.signals.task_failure.connect(crons_task_failure, weak=True)
        celery.signals.task_retry.connect(crons_task_retry, weak=True)

    # Connect signals
    celery.signals.worker_process_init.connect(worker_process_init, weak=True)
    celery.signals.before_task_publish.connect(before_task_publish, weak=False)
    celery.signals.task_prerun.connect(task_prerun, weak=True)
    celery.signals.task_postrun.connect(task_postrun, weak=True)

    celery._metrics_python_is_patched = True


def _patch_beat() -> None:
    """
    Patch Celery Beat and keep track of jobs using generics_heartbeats.
    """

    from celery.beat import Scheduler

    if hasattr(Scheduler, "_metrics_python_is_patched"):
        return

    original_apply_entry = Scheduler.apply_entry

    def metrics_python_apply_entry(*args: Any, **kwargs: Any) -> Any:
        _, schedule_entry = args

        # Capture scheduled task
        capture_checkin(
            name=schedule_entry.task,
            state=HeartbeatState.IN_PROGRESS,
        )

        return original_apply_entry(*args, **kwargs)

    Scheduler.apply_entry = metrics_python_apply_entry
    Scheduler._metrics_python_is_patched = True


def _register_beat_heartbeats() -> None:
    """
    Register beat entries as heartbeats.
    """

    from celery import app

    schedule = app.app_or_default().conf.beat_schedule

    for entry in schedule.values():
        task = entry["task"]
        schedule = entry["schedule"]

        seconds_between_runs: int = 0

        if isinstance(schedule, (int, float)):
            seconds_between_runs = int(schedule)
        elif isinstance(schedule, periodic_schedule):
            seconds_between_runs = schedule.seconds
        else:
            logger.warning(
                f"Task {task} is configured with schedule of type "
                f"{type(schedule)}, the schedule type is not supported "
                "by metrics-python."
            )
            continue

        grace_period_minutes = entry.get("options", {}).get("grace_period_minutes", 1)
        max_runtime_minutes = entry.get("options", {}).get("max_runtime_minutes", 10)

        register_heartbeat(
            name=task,
            seconds_between_runs=seconds_between_runs,
            grace_period_minutes=grace_period_minutes,
            max_runtime_minutes=max_runtime_minutes,
        )
