from src.eval.latency_eval import evaluate_latency_for_queries


def test_latency_eval_with_stream():
    def stream_fn(_query: str):
        yield "你好"
        yield "，世界"

    result = evaluate_latency_for_queries(["q1"], stream_fn)
    assert len(result.items) == 1
    m = result.items[0].metrics
    assert m["ttft_seconds"] >= 0
    assert m["total_seconds"] >= m["ttft_seconds"]
    assert m["chars_per_second"] >= 0
