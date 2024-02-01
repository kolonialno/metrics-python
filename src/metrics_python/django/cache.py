import functools
import time
from typing import TYPE_CHECKING, Any

from ._metrics import CACHE_CALL_DURATION, CACHE_CALL_GETS_DURATION

if TYPE_CHECKING:
    from django.core.cache import CacheHandler
    from django.core.cache.backends.base import BaseCache

METHODS_TO_INSTRUMENT = [
    "add",
    "delete",
    "delete_many",
    "get",
    "get_many",
    "has_key",
    "set",
    "set_many",
    "touch",
]

METHODS_WITH_RETURN_VALUE = ["get", "get_many"]


def _patch_cache_method(cache: "BaseCache", method_name: str, alias: str) -> None:
    def _instrument_call(
        method_name: str,
        alias: str,
        original_method: Any,
        args: Any,
        kwargs: Any,
    ) -> Any:
        start = time.perf_counter()
        value = original_method(*args, **kwargs)
        duration = time.perf_counter() - start

        CACHE_CALL_DURATION.labels(alias=alias, method=method_name).observe(duration)

        if method_name in METHODS_WITH_RETURN_VALUE:
            cache_hit = value is not None
            CACHE_CALL_GETS_DURATION.labels(
                alias=alias, method=method_name, hit=cache_hit
            ).observe(duration)

        return value

    original_method = getattr(cache, method_name)

    @functools.wraps(original_method)
    def patched_method(*args: Any, **kwargs: Any) -> Any:
        return _instrument_call(method_name, alias, original_method, args, kwargs)

    setattr(cache, method_name, patched_method)


def _patch_cache(cache: "BaseCache", alias: str) -> None:
    if not hasattr(cache, "_metrics_python_is_patched"):
        for method_name in METHODS_TO_INSTRUMENT:
            _patch_cache_method(cache, method_name, alias)

        cache._metrics_python_is_patched = True


def patch_caching() -> None:
    """
    Patch cache handler to observe cache calls.
    """

    from django.core import cache

    if not hasattr(cache.CacheHandler, "_metrics_python_is_patched"):
        original_create_connection = cache.CacheHandler.create_connection

        @functools.wraps(original_create_connection)
        def create_connection(self: "CacheHandler", alias: Any) -> Any:
            cache: "BaseCache" = original_create_connection(self, alias)

            _patch_cache(cache, alias)

            return cache

        cache.CacheHandler.create_connection = create_connection
        cache.CacheHandler._metrics_python_is_patched = True
