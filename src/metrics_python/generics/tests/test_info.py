from prometheus_client import REGISTRY

from metrics_python import __version__
from metrics_python.generics.info import expose_application_info


def test_info() -> None:
    expose_application_info(version="0.0.1", country="norway")

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_generics_info_application_info",
            {"version": "0.0.1", "country": "norway"},
        )
        == 1.0
    )

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_generics_info_application_version",
            {
                "application_version": "0.0.1",
                "metrics_python_version": __version__,
            },
        )
        == 1.0
    )
