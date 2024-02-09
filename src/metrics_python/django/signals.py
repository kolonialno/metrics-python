from functools import wraps
from typing import Any, Callable

from django import VERSION
from django.dispatch import Signal

from ._metrics import SIGNAL_DURATION


def _get_receiver_name(receiver: Callable[..., Any]) -> str:
    name = ""

    if hasattr(receiver, "__qualname__"):
        name = receiver.__qualname__
    elif hasattr(receiver, "__name__"):
        name = receiver.__name__
    elif hasattr(receiver, "func"):
        if hasattr(receiver, "func") and hasattr(receiver.func, "__name__"):
            name = "partial(<function " + receiver.func.__name__ + ">)"

    if name == "":
        return str(receiver)

    if hasattr(receiver, "__module__"):
        name = receiver.__module__ + "." + name

    return name


def patch_signals() -> None:
    if hasattr(Signal, "_metrics_python_is_patched"):
        return

    old_live_receivers = Signal._live_receivers

    def _metrics_python_live_receivers(self: Any, sender: Any) -> Any:
        if VERSION >= (5, 0):
            sync_receivers, async_receivers = old_live_receivers(self, sender)
        else:
            sync_receivers = old_live_receivers(self, sender)
            async_receivers = []

        def metrics_python_sync_receiver_wrapper(receiver: Any) -> Any:
            @wraps(receiver)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                signal = _get_receiver_name(receiver)

                with SIGNAL_DURATION.labels(signal=signal).time():
                    return receiver(*args, **kwargs)

            return wrapper

        for idx, receiver in enumerate(sync_receivers):
            sync_receivers[idx] = metrics_python_sync_receiver_wrapper(receiver)

        if VERSION >= (5, 0):
            return sync_receivers, async_receivers
        else:
            return sync_receivers

    Signal._live_receivers = _metrics_python_live_receivers
    Signal._metrics_python_is_patched = True
