from celery import signals

from metrics_python.celery import setup_celery_metrics


def test_setup_celery_signals() -> None:
    # Setup celery metrics multiple times
    setup_celery_metrics()
    setup_celery_metrics()

    # Make sure we just added one signal handler
    assert len(signals.worker_process_init.receivers) == 1
