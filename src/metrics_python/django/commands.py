from functools import wraps
from typing import Any

from django.core.management import BaseCommand

from metrics_python.prometheus import push_metrics

from ._metrics import (
    MANAGEMENT_COMMAND_DUPLICATE_QUERY_COUNT,
    MANAGEMENT_COMMAND_DURATION,
    MANAGEMENT_COMMAND_QUERY_COUNT,
    MANAGEMENT_COMMAND_QUERY_DURATION,
    MANAGEMENT_COMMAND_QUERY_REQUESTS_COUNT,
)
from ._query_counter import QueryCounter


def _measure_command(*, command: str, counter: QueryCounter) -> None:
    labels = {"command": command}

    MANAGEMENT_COMMAND_QUERY_REQUESTS_COUNT.labels(**labels).inc()

    for (
        db,
        query_duration,
    ) in counter.get_total_query_duration_seconds_by_alias().items():
        MANAGEMENT_COMMAND_QUERY_DURATION.labels(db=db, **labels).observe(
            query_duration
        )

    for (
        db,
        query_count,
    ) in counter.get_total_query_count_by_alias().items():
        MANAGEMENT_COMMAND_QUERY_COUNT.labels(db=db, **labels).inc(query_count)

    for (
        db,
        query_count,
    ) in counter.get_total_duplicate_query_count_by_alias().items():
        MANAGEMENT_COMMAND_DUPLICATE_QUERY_COUNT.labels(db=db, **labels).inc(
            query_count
        )


def patch_commands() -> None:
    """Patch management commands."""

    old_execute = BaseCommand.execute

    def execute(self: Any, *args: Any, **kwargs: Any) -> Any:
        from .conf import settings

        # Push metrics when the job complete.
        with push_metrics(job=settings.JOB, gateway=settings.PUSHGATEWAY):
            with (
                # Measure command duration.
                MANAGEMENT_COMMAND_DURATION.labels(command=self.__module__).time(),
                # Measure database queries
                QueryCounter.create_as_current() as counter,
            ):
                value = old_execute(self, *args, **kwargs)

                _measure_command(command=self.__module__, counter=counter)

                return value

    BaseCommand.execute = wraps(old_execute)(execute)
