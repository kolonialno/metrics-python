import os
from datetime import timedelta
from typing import Any

from gunicorn.glogging import Logger
from gunicorn.http.message import Request
from gunicorn.http.wsgi import Response

from ._metrics import (
    ACTIVE_WORKER_SECONDS,
    ACTIVE_WORKERS,
    LOG_RECORDS,
    REQUEST_DURATION,
    REQUESTS_HANDLED_BY_WORKER,
)


class Prometheus(Logger):  # type: ignore
    """
    Prometheus-based instrumentation, that passes as a logger.

    This is equivalent to the StatsD implementation from Gunicorn.
    """

    def critical(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("critical", msg, *args, **kwargs)

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("error", msg, *args, **kwargs)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("warning", msg, *args, **kwargs)

    def exception(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("exception", msg, *args, **kwargs)

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("info", msg, *args, **kwargs)

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._handle_log("debug", msg, *args, **kwargs)

    def _handle_log(
        self, method_name: str, msg: Any, *args: Any, **kwargs: Any
    ) -> None:
        logfunc = getattr(Logger, method_name)
        logfunc(self, msg, *args, **kwargs)

        LOG_RECORDS.labels(level=method_name).inc()

        extra = kwargs.get("extra", None)
        if extra:
            self._handle_metric(
                metric=extra.get("metric"),
                value=extra.get("value"),
                mtype=extra.get("mtype"),
            )

    def _handle_metric(self, *, metric: Any, value: Any, mtype: Any) -> None:
        if not (metric and value and mtype):
            return

        # gunicorn.workers: number of workers managed by the arbiter (gauge)
        # https://docs.gunicorn.org/en/stable/instrumentation.html
        if metric == "gunicorn.workers":
            assert mtype == "gauge"
            ACTIVE_WORKERS.set(value)

    def access(
        self,
        resp: Response,
        req: Request,
        environ: dict[str, Any],
        request_time: timedelta,
    ) -> None:
        super().access(resp, req, environ, request_time)

        status = resp.status
        if isinstance(status, str):
            status = int(status.split(None, 1)[0])

        worker_pid = os.getpid()

        duration_in_seconds = request_time.total_seconds()

        REQUEST_DURATION.labels(status=status, worker=worker_pid).observe(
            duration_in_seconds
        )
        ACTIVE_WORKER_SECONDS.inc(duration_in_seconds)
