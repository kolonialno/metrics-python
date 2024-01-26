import os
import re
from logging import getLogger
from pathlib import Path

import prometheus_client
import prometheus_client.multiprocess
from prometheus_client.registry import Collector, CollectorRegistry

logger = getLogger(__name__)


def _parse_bool(value: str) -> bool:
    val = value.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"invalid truth value {val}")


def _wipe_prometheus_dir(prometheus_dir: Path) -> None:
    # This shouldn't be necessary in prod, but it's a convenience when
    # testing locally.

    assert prometheus_dir.exists()
    assert prometheus_dir.is_dir()

    master_pid = os.getpid()

    PATTERN_RE = re.compile(r"^[a-z_]+_([0-9]+).db$")

    for filepath in prometheus_dir.iterdir():
        m = PATTERN_RE.match(filepath.name)
        if not m:
            raise RuntimeError(
                f"File already exists in {str(prometheus_dir)} not matching "
                f"known pattern: {str(filepath)}"
            )

        if master_pid == int(m.group(1)):
            # A file from this process. Let it be.
            continue

        logger.warning(
            "Removing leftover file from previous Prometheus process: %s", filepath
        )
        filepath.unlink()


def start_prometheus_background_server(
    *,
    port: int | None = None,
    multiprocess: bool = False,
    collectors: list[Collector] | None = None,
) -> None:
    # Lookup properties needed to configure prometheus
    prometheus_enabled = _parse_bool(os.environ.get("PROMETHEUS_ENABLED", "false"))
    prometheus_port = port or int(os.environ.get("PROMETHEUS_METRICS_PORT", "8001"))
    prometheus_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")

    if not prometheus_enabled:
        return

    if not multiprocess:
        logger.info("Listening for metrics; metrics_port=%r", prometheus_port)
        prometheus_client.start_http_server(prometheus_port)
        return

    # Make sure we have the multiproc dir if multiprocess metrics
    # gathering is enabled.
    if multiprocess and not prometheus_multiproc_dir:
        logger.info("Prometheus is disabled; PROMETHEUS_MULTIPROC_DIR not set")
        return

    registry = CollectorRegistry()

    # Can add more collectors here to run things on-demand at scrape time.
    # Make sure they don't use regular metrics though. Since then the collector
    # will run and the exported multiprocess value in the multiproc dir will
    # both be picked up! See here:
    # https://github.com/prometheus/client_python#multiprocess-mode-eg-gunicorn
    # Quote: "Registering metrics to a registry later used by a
    #         MultiProcessCollector may cause duplicate metrics to be exported"
    if collectors:
        for collector in collectors:
            registry.register(collector)

    assert prometheus_multiproc_dir
    prometheus_multiproc_dir_path = Path(prometheus_multiproc_dir)

    logger.info(
        "Starting Prometheus background server; directory:%r metrics_port:%r",
        str(prometheus_multiproc_dir_path),
        prometheus_port,
    )

    _wipe_prometheus_dir(prometheus_multiproc_dir_path)

    prometheus_client.multiprocess.MultiProcessCollector(registry)  # type: ignore

    logger.info("Listening for metrics; metrics_port=%r", prometheus_port)
    prometheus_client.start_http_server(prometheus_port, registry=registry)


def mark_process_dead(pid: int) -> None:
    prometheus_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")

    if prometheus_multiproc_dir:
        logger.info("Marking child as dead")
        prometheus_client.multiprocess.mark_process_dead(pid)  # type: ignore
