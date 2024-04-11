import hashlib
import time
from functools import cached_property
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterator

from strawberry.extensions import LifecycleStep, SchemaExtension
from strawberry.extensions.tracing.utils import should_skip_tracing

from ._metrics import LIFECYCLE_STEP_DURATION, OPERATION_DURATION

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo


class PrometheusExtension(SchemaExtension):
    @cached_property
    def _resource_name(self) -> str:
        assert self.execution_context.query

        query_hash = self.hash_query(self.execution_context.query)

        if self.execution_context.operation_name:
            return f"{self.execution_context.operation_name}:{query_hash}"

        return query_hash

    def hash_query(self, query: str) -> str:
        return hashlib.md5(query.encode("utf-8")).hexdigest()

    def on_operation(self) -> Iterator[None]:
        start_time = time.perf_counter()

        assert self.execution_context.query

        operation_name = str(self.execution_context.operation_name)

        operation_type = "query"
        if self.execution_context.query.strip().startswith("mutation"):
            operation_type = "mutation"
        elif self.execution_context.query.strip().startswith("subscription"):
            operation_type = "subscription"

        yield

        duration = time.perf_counter() - start_time

        OPERATION_DURATION.labels(
            operation_name=operation_name or "Anonymous Query",
            resource=self._resource_name,
            operation_type=operation_type,
            backend="strawberry",
        ).observe(duration)
        LIFECYCLE_STEP_DURATION.labels(
            lifecycle_step=LifecycleStep.OPERATION, backend="strawberry"
        ).observe(duration)

    def on_validate(self) -> Generator[None, None, None]:
        start_time = time.perf_counter()

        yield

        duration = time.perf_counter() - start_time

        LIFECYCLE_STEP_DURATION.labels(
            lifecycle_step=LifecycleStep.VALIDATION, backend="strawberry"
        ).observe(duration)

    def on_parse(self) -> Generator[None, None, None]:
        start_time = time.perf_counter()

        yield

        duration = time.perf_counter() - start_time

        LIFECYCLE_STEP_DURATION.labels(
            lifecycle_step=LifecycleStep.PARSE, backend="strawberry"
        ).observe(duration)

    async def resolve(
        self,
        _next: Callable[..., Any],
        root: Any,
        info: "GraphQLResolveInfo",
        *args: str,
        **kwargs: Any,
    ) -> Any:
        if should_skip_tracing(_next, info):
            result = _next(root, info, *args, **kwargs)

            if isawaitable(result):  # pragma: no cover
                result = await result

            return result

        start_time = time.perf_counter()

        result = _next(root, info, *args, **kwargs)

        if isawaitable(result):
            result = await result

        duration = time.perf_counter() - start_time

        LIFECYCLE_STEP_DURATION.labels(
            lifecycle_step=LifecycleStep.RESOLVE, backend="strawberry"
        ).observe(duration)

        return result


class PrometheusExtensionSync(PrometheusExtension):
    def resolve(
        self,
        _next: Callable[..., Any],
        root: Any,
        info: "GraphQLResolveInfo",
        *args: str,
        **kwargs: Any,
    ) -> Any:
        if should_skip_tracing(_next, info):
            return _next(root, info, *args, **kwargs)

        start_time = time.perf_counter()

        result = _next(root, info, *args, **kwargs)

        duration = time.perf_counter() - start_time

        LIFECYCLE_STEP_DURATION.labels(
            lifecycle_step=LifecycleStep.RESOLVE, backend="strawberry"
        ).observe(duration)

        return result
