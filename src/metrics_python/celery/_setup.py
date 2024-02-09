import celery

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

    # Celery signals has logic to prevent duplicate signal handlers,
    # but we keep the patched logic here to prevent issues in the
    # future if we decide to patch additional celery methods.
    if hasattr(celery, "_metrics_python_is_patched"):
        return

    # Connect signals
    celery.signals.worker_process_init.connect(worker_process_init, weak=True)
    celery.signals.before_task_publish.connect(before_task_publish, weak=False)
    celery.signals.task_prerun.connect(task_prerun, weak=True)
    celery.signals.task_postrun.connect(task_postrun, weak=True)

    celery._metrics_python_is_patched = True
