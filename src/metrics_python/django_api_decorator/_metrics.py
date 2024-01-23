from prometheus_client import Histogram

from ..constants import NAMESPACE

VIEW_DURATION = Histogram(
    "view_duration",
    "Time spent on a django-api-decorator view.",
    ["method", "view", "status"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django_api_decorator",
)
