import time
from typing import Callable, Iterable, List

from src.eval.types import EvalItemResult, EvalResult


StreamFn = Callable[[str], Iterable[str]]


def evaluate_latency_for_queries(queries: List[str], stream_fn: StreamFn) -> EvalResult:
    items: List[EvalItemResult] = []

    for idx, query in enumerate(queries, start=1):
        start = time.perf_counter()
        first_token_time = None
        char_count = 0

        for chunk in stream_fn(query):
            if chunk is None:
                continue
            if first_token_time is None:
                first_token_time = time.perf_counter()
            char_count += len(str(chunk))

        end = time.perf_counter()
        ttft = (first_token_time - start) if first_token_time else (end - start)
        total = end - start
        speed = char_count / total if total > 0 else 0.0

        items.append(
            EvalItemResult(
                case_id=f"latency_{idx}",
                metrics={
                    "ttft_seconds": ttft,
                    "total_seconds": total,
                    "chars_per_second": speed,
                },
                extra={"query": query, "chars": char_count},
            )
        )

    count = max(len(items), 1)
    summary = {
        "ttft_seconds": sum(i.metrics["ttft_seconds"] for i in items) / count,
        "total_seconds": sum(i.metrics["total_seconds"] for i in items) / count,
        "chars_per_second": sum(i.metrics["chars_per_second"] for i in items) / count,
    }
    return EvalResult(items=items, summary=summary)
