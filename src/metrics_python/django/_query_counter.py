import collections
import contextlib
import time
import traceback
from logging import getLogger
from types import FrameType
from typing import Any, Generator

from django.db import connections
from django.template import Node

from .conf import settings

logger = getLogger(__name__)


def yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


class QueryCounter:
    """Query counter."""

    compress_stacktrace = True

    def __init__(self) -> None:
        self.query_count: collections.Counter[str] = collections.Counter()
        self.duration_count: collections.Counter[str] = collections.Counter()

        self.stack_summaries: list[tuple[traceback.StackSummary, str]] = []
        self.stacks: list[list[tuple[FrameType, int]]] = []
        self.duplicate_count: collections.Counter[tuple[str, int]] = (
            collections.Counter()
        )

    def __call__(
        self, execute: Any, sql: Any, params: Any, many: Any, context: Any
    ) -> Any:
        alias = context["connection"].alias

        if settings.OBSERVE_DUPLICATE_QUERIES:
            stack = list(reversed(list(traceback.walk_stack(None))))

            # StackSummary is used for comparison (have we seen this stack
            # before?).
            stack_summary = traceback.StackSummary.extract(stack)

            # If the same SQL came from the same stack trace previously,
            # it is considered as a duplicate.
            if (stack_summary, sql) in self.stack_summaries:
                index = self.stack_summaries.index((stack_summary, sql))
                # self.duplicates needs to be indexed with a number because
                # StackSummary is not hashable.
                self.duplicate_count[(alias, index)] += 1
            else:
                self.stack_summaries.append((stack_summary, sql))

                if settings.PRINT_DUPLICATE_QUERIES:
                    self.stacks.append(stack)

        try:
            start = time.perf_counter_ns()
            return execute(sql, params, many, context)
        finally:
            duration = time.perf_counter_ns() - start

            self.query_count[alias] += 1
            self.duration_count[alias] += duration

    def get_total_query_count(self) -> int:
        return self.query_count.total()

    def get_total_query_count_by_alias(self) -> dict[str, int]:
        return self.query_count

    def get_total_query_duration_seconds(self) -> float:
        return self.duration_count.total() / 10.0**9

    def get_total_query_duration_seconds_by_alias(self) -> dict[str, float]:
        return {
            alias: duration / 10.0**9 for alias, duration in self.duration_count.items()
        }

    def get_total_duplicate_query_count(self) -> int:
        return self.duplicate_count.total()

    def get_total_duplicate_query_count_by_alias(self) -> dict[str, int]:
        return {alias: count for (alias, _), count in self.duplicate_count.items()}

    def print_duplicate_queries(self) -> None:  # noqa: C901
        if not self.duplicate_count:
            return

        print(yellow("\nDuplicate queries detected!"))

        for duplicate, count in self.duplicate_count.items():
            alias, stack_index = duplicate
            stack_summary, sql = self.stack_summaries[stack_index]
            stack_raw = self.stacks[stack_index]

            gap = False
            for formatted, (frame, _) in zip(stack_summary.format(), stack_raw):
                filename = frame.f_code.co_filename
                is_package = "site-packages" in filename
                f_locals = frame.f_locals
                is_template_node = "self" in f_locals and isinstance(
                    f_locals["self"], Node
                )

                if self.compress_stacktrace and is_package and not is_template_node:
                    if not gap:
                        print("  ", end="")
                    print(".", end="")
                    gap = True
                    continue

                if gap:
                    print()

                if is_template_node:
                    node = f_locals["self"]

                    # There is usually multiple stack frames that process the same template line. For this rendering,
                    # we just want to show the template stack, so we can ignore any frames that have an identical Node
                    # as their predecessor.
                    if frame.f_back:
                        parent_locals = frame.f_back.f_locals
                        parent_is_template = "self" in parent_locals and isinstance(
                            parent_locals["self"], Node
                        )
                        if parent_is_template:
                            parent_node = parent_locals["self"]
                            if parent_node == node:
                                continue

                    print(f'  File "{node.origin.name}", line {node.token.lineno}')
                    print(f"    {node.token.contents}")
                else:
                    print(formatted, end="")

                gap = False

            print(yellow(f"\n^^ The above query was executed {count + 1} times ^^\n"))

        print(
            f"Total of {len(self.duplicate_count)} duplicate queries "
            f"({self.get_total_duplicate_query_count()} executions)"
        )

    @contextlib.contextmanager
    @staticmethod
    def create_counter() -> Generator["QueryCounter", None, None]:
        counter = QueryCounter()

        with contextlib.ExitStack() as stack:
            for alias in connections:
                stack.enter_context(
                    connections[alias].execute_wrapper(counter),
                )

            yield counter

            if settings.PRINT_DUPLICATE_QUERIES:
                counter.print_duplicate_queries()
