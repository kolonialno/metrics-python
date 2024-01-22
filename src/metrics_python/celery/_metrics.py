from prometheus_client import Counter, Gauge, Histogram

from ..constants import NAMESPACE

TASK_EXECUTION_DELAY = Histogram(
    "task_execution_delay",
    "Time spent in the messaging queue before a worker starts executing a task",
    ["task", "queue"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="celery",
)

TASKS_EXECUTED = Counter(
    "celery_tasks_executed",
    "Celery tasks executed, by name and state",
    ["task", "queue", "state"],
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
    namespace=NAMESPACE,
    subsystem="celery",
)
