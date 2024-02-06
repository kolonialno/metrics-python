import contextlib
from typing import Generator
from urllib.error import URLError

from prometheus_client import CollectorRegistry, push_to_gateway


@contextlib.contextmanager
def push_metrics(
    *,
    registry: CollectorRegistry,
    job: str,
    gateway: str | None = None,
    timeout: int = 5,
) -> Generator[None, None, None]:
    """
    Helper util used to push prometheus metrics to a pushgateway in
    ephemeral and batch jobs. This is designed to be used in short-lived
    management commands only, long-running jobs should use the metrics
    server instead.

    Example:

    # Define the registry with metrics you want to push.
    registry = CollectorRegistry()

    # Define the metrics you want to push
    counter = Counter('name', registry=registry, ...)

    # Run logic inside the push_metrics context nanager.
    with push_metrics(registry=registry, job="<app>", gateway="<pushgateway>"):
        ...
        counter.inc()
        ...
    """

    yield

    # Push metrics in registry to the configured pushgateway.
    try:
        if gateway:
            push_to_gateway(
                gateway=gateway,
                job="job",
                registry=registry,
                timeout=timeout,
            )
    except URLError:
        pass
