from prometheus_client import REGISTRY

from metrics_python.django.cache import patch_caching


def test_patch_cache() -> None:
    # Patch multiple times, it should not affect our metrics.
    patch_caching()
    patch_caching()

    from django.core.cache import cache

    cache.set("test", "value")
    cache.get("test")
    cache.get("unknown")

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_cache_call_duration_seconds_count",
            {"alias": "default", "method": "set"},
        )
        == 1.0
    )

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_cache_call_duration_seconds_count",
            {"alias": "default", "method": "get"},
        )
        == 2.0
    )

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_cache_call_gets_duration_seconds_count",
            {"alias": "default", "method": "get", "hit": "True"},
        )
        == 1.0
    )

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_cache_call_gets_duration_seconds_count",
            {"alias": "default", "method": "get", "hit": "False"},
        )
        == 1.0
    )
