from celery import signals

from ._signals import (
    before_task_publish,
    task_postrun,
    task_prerun,
    worker_process_init,
)


def setup_celery_metrics() -> None:
    """
    Patch celery to export metrics.
    """

    # Connect signals
    signals.worker_process_init.connect(worker_process_init, weak=True)
    signals.before_task_publish.connect(before_task_publish, weak=False)
    signals.task_prerun.connect(task_prerun, weak=True)
    signals.task_postrun.connect(task_postrun, weak=True)
