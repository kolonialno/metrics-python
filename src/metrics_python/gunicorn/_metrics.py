from prometheus_client import Counter, Histogram

from ..constants import NAMESPACE

REQUEST_DURATION = Histogram(
    "request_duration",
    "Time spent on processing a request in Gunicorn",
    ["status"],
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
