import logging
import time
from enum import StrEnum
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from prometheus_client import Gauge, Summary

from metrics_python.django.signals import _get_receiver_name

from ..constants import NAMESPACE

Param = ParamSpec("Param")
RetType = TypeVar("RetType")

logger = logging.getLogger(__name__)

HEARTBEAT_LAST_CHECKIN = Gauge(
    "last_checkin",
    "Time of last heartbeat checkin.",
    ["name", "state"],
    multiprocess_mode="mostrecent",
    namespace=NAMESPACE,
    subsystem="generics_heartbeats",
)

HEARTBEAT_EXECUTION_DURATION = Summary(
    "execution_duration",
    "Time spent executing the heartbeat job.",
    ["name", "state"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="generics_heartbeats",
)


class HeartbeatState(StrEnum):
    IN_PROGRESS = "in-progress"
    OK = "ok"
    ERROR = "error"


def capture_checkin(
    name: str, state: HeartbeatState, duration_seconds: float | None = None
) -> None:
    """
    Capture heartbeat checkin.
    """

    # Register last checkin.
    HEARTBEAT_LAST_CHECKIN.labels(name=name, state=state).set_to_current_time()

    # Register execution duration is state is OK or ERROR.
    if duration_seconds and state in [HeartbeatState.OK, HeartbeatState.ERROR]:
        HEARTBEAT_EXECUTION_DURATION.labels(name=name, state=state).observe(
            duration_seconds
        )


HEARTBEAT_REGISTRY: dict[str, dict[str, Any]] = {}


def register_heartbeat(
    *,
    name: str,
    seconds_between_runs: int,
    grace_period_minutes: int = 1,
    max_runtime_minutes: int = 10,
) -> None:
    """
    Register heartbeat in the heartbeat registry. This is used to generate
    alerts.
    """

    if seconds_between_runs < 60:
        logger.warning(
            f"Intervals shorter than one minute is not supported by "
            f"metrics-python. Heartbeat {name} is configured with an "
            f"interval of {seconds_between_runs} seconds."
        )
        return

    HEARTBEAT_REGISTRY[name] = {
        "seconds_between_runs": seconds_between_runs,
        "grace_period_minutes": grace_period_minutes,
        "max_runtime_minutes": max_runtime_minutes,
    }


def observe_heartbeat(
    *,
    seconds_between_runs: int,
    grace_period_minutes: int = 1,
    max_runtime_minutes: int = 10,
) -> Callable[[Callable[Param, RetType]], Callable[Param, RetType]]:
    def decorator(f: Callable[Param, RetType]) -> Callable[Param, RetType]:
        name = _get_receiver_name(f)

        # Register heartbeat
        register_heartbeat(
            name=name,
            seconds_between_runs=seconds_between_runs,
            grace_period_minutes=grace_period_minutes,
            max_runtime_minutes=max_runtime_minutes,
        )

        @wraps(f)
        def inner(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
            # Register checkins and execute the decorated method
            capture_checkin(name=name, state=HeartbeatState.IN_PROGRESS)

            start = time.perf_counter()

            try:
                result = f(*args, **kwargs)

                capture_checkin(
                    name=name,
                    state=HeartbeatState.OK,
                    duration_seconds=time.perf_counter() - start,
                )

                return result
            except Exception:
                capture_checkin(
                    name=name,
                    state=HeartbeatState.ERROR,
                    duration_seconds=time.perf_counter() - start,
                )

                raise

        return inner

    return decorator
