from prometheus_client import Gauge

from ..constants import NAMESPACE

WORKERS_BY_STATE = Gauge(
    "workers_by_state",
    "Number of workers by state (busy or idle) and worker type "
    "(gunicorn, celery, etc.)",
    ["worker_type", "state"],
    multiprocess_mode="livesum",
    namespace=NAMESPACE,
    subsystem="generics_workers",
)


def export_worker_busy_state(*, worker_type: str, busy: bool) -> None:
    """
    Mark a process worker as busy or idle, this can be used to keep track
    of worker usage in systems like gunicorn or celery.
    """

    if busy:
        WORKERS_BY_STATE.labels(state="busy", worker_type=worker_type).set(1)
        WORKERS_BY_STATE.labels(state="idle", worker_type=worker_type).set(0)
    else:
        WORKERS_BY_STATE.labels(state="busy", worker_type=worker_type).set(0)
        WORKERS_BY_STATE.labels(state="idle", worker_type=worker_type).set(1)
