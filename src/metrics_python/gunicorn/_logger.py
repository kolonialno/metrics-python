from datetime import timedelta
from typing import Any

from gunicorn.glogging import Logger
from gunicorn.http.message import Request
from gunicorn.http.wsgi import Response

from ._metrics import LOG_RECORDS, REQUEST_DURATION


class Prometheus(Logger):  # type: ignore
    """
    Prometheus-based instrumentation, that passes as a logger.

    This is equivalent to the StatsD implementation from Gunicorn.
    """

    def critical(self, *args: Any, **kwargs: Any) -> None:
        super().critical(*args, **kwargs)

        LOG_RECORDS.labels(level="critical").inc()

    def error(self, *args: Any, **kwargs: Any) -> None:
        super().error(*args, **kwargs)

        LOG_RECORDS.labels(level="error").inc()

    def warning(self, *args: Any, **kwargs: Any) -> None:
        super().warning(*args, **kwargs)

        LOG_RECORDS.labels(level="warning").inc()

    def exception(self, *args: Any, **kwargs: Any) -> None:
        super().exception(*args, **kwargs)

        LOG_RECORDS.labels(level="exception").inc()

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

        REQUEST_DURATION.labels(status=status).observe(request_time.total_seconds())
