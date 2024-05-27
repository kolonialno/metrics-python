from prometheus_client import Counter, Gauge, Histogram

from ..constants import NAMESPACE

TASK_PUBLISHED = Counter(
    "task_published",
    "Number of published tasks.",
    ["task", "routing_key"],
    namespace=NAMESPACE,
    subsystem="celery",
)

TASK_APPLY_DURATION = Histogram(
    "task_apply_duration",
    "Time spent applying the task",
    ["task"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="celery",
)

TASK_EXECUTION_DELAY = Histogram(
    "task_execution_delay",
    "Time spent in the messaging queue before a worker starts executing a task",
    ["task", "queue"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="celery",
)

TASK_EXECUTION_DURATION = Histogram(
    "task_execution_duration",
    "Time spent executing the task",
    ["task", "queue", "state"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="celery",
)

TASK_LAST_EXECUTION = Gauge(
    "task_last_execution",
    "Last time a task was executed",
    ["task", "queue", "state"],
    multiprocess_mode="mostrecent",
    namespace=NAMESPACE,
    subsystem="celery",
)
