from prometheus_client import Gauge, Info

from metrics_python import __version__

from ..constants import NAMESPACE

APPLICATION_INFO = Info(
    "application",
    "Information about the running target from metrics-python",
    namespace=NAMESPACE,
    subsystem="generics_info",
)

# We keep a separate Gauge with the application version. This is
# needed since the Info() metric is not supported when the application
# runs in multiprocess mode.
APPLICATION_VERSION = Gauge(
    "application_version",
    "Information about the current running version of the application.",
    ["application_version", "metrics_python_version"],
    multiprocess_mode="livemostrecent",
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
    APPLICATION_VERSION.labels(
        application_version=version,
        metrics_python_version=__version__,
    ).set(1.0)
