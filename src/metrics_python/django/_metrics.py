from prometheus_client import Counter

from ..constants import NAMESPACE

QUERY_COUNT_BY_VIEW = Counter(
    "query_count_by_view",
    "Number of database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

QUERY_DURATION_BY_VIEW = Counter(
    "query_duration_by_view",
    "Database query duration by views.",
    ["db", "method", "view", "status"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

DUPLICATE_QUERY_COUNT_BY_VIEW = Counter(
    "duplicate_query_count_by_view",
    "Number of duplicate database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)
