import os
from datetime import timedelta
from typing import Any

from gunicorn.glogging import Logger
from gunicorn.http.message import Request
from gunicorn.http.wsgi import Response

from ._metrics import ACTIVE_WORKERS, LOG_RECORDS, REQUEST_DURATION


class Prometheus(Logger):  # type: ignore
    """
    Prometheus-based instrumentation, that passes as a logger.

    This is equivalent to the StatsD implementation from Gunicorn.
    """

    def critical(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("critical", *args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("error", *args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("warning", *args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("exception", *args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("info", *args, **kwargs)

    def debug(self, *args: Any, **kwargs: Any) -> None:
        self._handle_log("debug", *args, **kwargs)

    def _handle_log(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        logfunc = getattr(Logger, method_name)
        logfunc(self, *args, **kwargs)

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

        REQUEST_DURATION.labels(status=status, worker_pid=worker_pid).observe(
            duration_in_seconds
        )
