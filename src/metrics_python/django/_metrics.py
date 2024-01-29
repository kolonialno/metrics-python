from prometheus_client import Counter, Histogram

from ..constants import NAMESPACE

#
# Django view query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a view.
VIEW_QUERY_REQUESTS_COUNT = Counter(
    "view_query_request_count",
    "Number of requests sent to a view.",
    ["method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_QUERY_DURATION = Histogram(
    "view_query_duration",
    "Database query duration by views.",
    ["db", "method", "view", "status"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_QUERY_COUNT = Counter(
    "view_query_count",
    "Number of database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_DUPLICATE_QUERY_COUNT = Counter(
    "view_duplicate_query_count",
    "Number of duplicate database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Django Celery task query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a task.
CELERY_QUERY_REQUESTS_COUNT = Counter(
    "celery_query_request_count",
    "Number of requests sent to a celery task.",
    ["task"],
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_QUERY_DURATION = Histogram(
    "celery_query_duration",
    "Database query duration by celery tasks.",
    ["db", "task"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_QUERY_COUNT = Counter(
    "celery_query_count",
    "Number of database queries executed by celery tasks.",
    ["db", "task"],
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_DUPLICATE_QUERY_COUNT = Counter(
    "celery_duplicate_query_count",
    "Number of duplicate database queries executed by celery tasks.",
    ["db", "task"],
    namespace=NAMESPACE,
    subsystem="django",
)
