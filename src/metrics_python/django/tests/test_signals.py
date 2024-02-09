from django.dispatch import Signal
from prometheus_client import REGISTRY
from pytest_mock import MockerFixture

from metrics_python.django.signals import patch_signals


def test_patch_signal(mocker: MockerFixture) -> None:
    # Create a test signal
    test_signal = Signal()

    # Connect mock to signal
    mock = mocker.Mock()
    setattr(mock, "__qualname__", "TestMock")  # noqa
    test_signal.connect(mock)

    # Patch signals twise, we should only measure the signal execution once.
    patch_signals()
    patch_signals()

    # Trigger signal
    test_signal.send(test_patch_signal)

    # Mock is called once
    mock.assert_called_once()

    # We should only have one measurement in our prometheus metrics
    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_signal_duration_seconds_count",
            {"signal": "unittest.mock.TestMock"},
        )
        == 1.0
    )
