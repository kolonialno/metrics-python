from prometheus_client import Info

from ..constants import NAMESPACE

APPLICATION_INFO = Info(
    "application",
    "Information about the running target from metrics-python",
    namespace=NAMESPACE,
    subsystem="generics_info",
)


def expose_application_info(*, version: str, **extra: str) -> None:
    """
    Expose additional application data using a prometheus metric.

    This is used in Grafana to access data we can't easily can lookup
    elsewhere.
    """

    labels: dict[str, str] = {"version": version, **extra}

    APPLICATION_INFO.info(labels)
