from django.core.management import call_command
from prometheus_client import REGISTRY

from metrics_python.django.commands import patch_commands


def test_patch_commands() -> None:
    # Patch commands multiple times
    patch_commands()
    patch_commands()

    # Execute command
    call_command("test")

    # We should only have one measurement in our prometheus metrics
    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_management_command_duration_seconds_count",
            {"command": "metrics_python.django.tests.app.management.commands.test"},
        )
        == 1.0
    )
