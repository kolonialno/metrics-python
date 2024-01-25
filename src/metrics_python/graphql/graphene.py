import time

from graphql import GraphQLResolveInfo
from graphql.language import OperationDefinitionNode

from ._metrics import OPERATION_DURATION, RESOLVE_DURATION


class MetricsMiddleware:
    def resolve(self, next, root, info: GraphQLResolveInfo, **args):
        start = time.perf_counter()

        return_value = next(root, info, **args)

        duration = time.perf_counter() - start

        operation: OperationDefinitionNode | None = getattr(info, "operation", None)

        if root is None:
            operation_name = (
                str(operation.name.value)
                if operation.name
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
            ).observe(duration)

        RESOLVE_DURATION.labels(
            field_path=f"{info.parent_type}.{info.field_name}",
            field_name=info.field_name,
            parent_type=info.parent_type.name,
            path=".".join(map(str, info.path.as_list())),
        ).observe(duration)

        return return_value
