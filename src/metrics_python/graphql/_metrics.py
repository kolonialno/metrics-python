from prometheus_client import Histogram

from ..constants import NAMESPACE

OPERATION_DURATION = Histogram(
    "operation_duration",
    "Time spent on a GraphQL operation.",
    ["operation_name", "resource", "operation_type", "backend"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="graphql",
)


LIFECYCLE_STEP_DURATION = Histogram(
    "lifecycle_step_duration",
    "Time spent on validating or parsing a query.",
    ["lifecycle_step", "backend"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="graphql",
)
