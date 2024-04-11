import time
from typing import Any

from graphql import GraphQLResolveInfo
from graphql.language import OperationDefinitionNode

from ._metrics import OPERATION_DURATION


class MetricsMiddleware:
    def resolve(
        self, next: Any, root: Any, info: GraphQLResolveInfo, **args: Any
    ) -> Any:
        start = time.perf_counter()

        return_value = next(root, info, **args)

        duration = time.perf_counter() - start

        operation: OperationDefinitionNode | None = getattr(info, "operation", None)

        if root is None:
            operation_name = (
                str(operation.name.value)
                if operation and operation.name
                else "Unknown operation name"
            )

            OPERATION_DURATION.labels(
                operation_name=operation_name,
                # The strawberry integration uses
                # "{operation_name}:{query_hash}" as resource.
                # We ignore the hash in the graphene integration, it
                # is strictly not needed.
                resource=operation_name,
                operation_type=(
                    str(operation.operation.value)
                    if operation
                    else "Unknown operation type"
                ),
                backend="graphene",
            ).observe(duration)

        return return_value
