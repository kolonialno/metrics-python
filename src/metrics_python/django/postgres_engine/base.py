from typing import Any

from django.db.backends.postgresql import base

from metrics_python.django._metrics import (
    DATABASE_GET_NEW_CONNECTION_HISTOGRAM,
    DATABASE_INIT_CONNECTION_STATE_HISTOGRAM,
)


class DatabaseWrapper(base.DatabaseWrapper):  # type: ignore
    def get_new_connection(self, conn_params: dict[str, Any]) -> Any:
        with DATABASE_GET_NEW_CONNECTION_HISTOGRAM.labels(
            database_host=conn_params.get("host", "unknown"),
            database_port=conn_params.get("port", "unknown"),
            database_name=conn_params.get("dbname", "unknown"),
            database_username=conn_params.get("user", "unknown"),
        ).time():
            return super().get_new_connection(conn_params)

    def init_connection_state(self) -> Any:
        conn_params = self.get_connection_params()
        with DATABASE_INIT_CONNECTION_STATE_HISTOGRAM.labels(
            database_host=conn_params.get("host", "unknown"),
            database_port=conn_params.get("port", "unknown"),
            database_name=conn_params.get("dbname", "unknown"),
            database_username=conn_params.get("user", "unknown"),
        ).time():
            return super().init_connection_state()
