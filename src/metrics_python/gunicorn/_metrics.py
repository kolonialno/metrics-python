from prometheus_client import Counter, Gauge, Histogram

from ..constants import NAMESPACE

REQUEST_DURATION = Histogram(
    "request_duration",
    "Time spent on processing a request in Gunicorn",
    ["status", "worker"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="gunicorn",
)

LOG_RECORDS = Counter(
    "log_records",
    "The number of log records emitted by Gunicorn.",
    ["level"],
    namespace=NAMESPACE,
    subsystem="gunicorn",
)


ACTIVE_WORKERS = Gauge(
    "workers",
    "Active gunicorn workers",
    namespace=NAMESPACE,
    subsystem="gunicorn",
)

ACTIVE_WORKER_SECONDS = Counter(
    "active_worker_seconds",
    "Total worker-seconds spent processing requests",
    namespace=NAMESPACE,
    subsystem="gunicorn",
)
