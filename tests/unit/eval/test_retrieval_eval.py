from src.eval.retrieval_eval import evaluate_retrieval, hit_at_k, recall_at_k, mrr_at_k
from src.eval.types import EvalCase


def test_metric_functions():
    expected = ["d2", "d9"]
    predicted = ["d1", "d2", "d3"]
    assert hit_at_k(expected, predicted, 3) == 1.0
    assert recall_at_k(expected, predicted, 3) == 0.5
    assert mrr_at_k(expected, predicted, 3) == 0.5


def test_evaluate_retrieval_aggregate():
    cases = [
        EvalCase(case_id="c1", query="q1", expected_docids=["d1"], difficulty="easy"),
        EvalCase(case_id="c2", query="q2", expected_docids=["d9"], difficulty="easy"),
    ]

    def mock_retrieve(query: str, k: int):
        if query == "q1":
            return ["d1", "d2"]
        return ["d3", "d4"]

    result = evaluate_retrieval(cases, mock_retrieve, k=2)
    assert result.summary["hit_at_k"] == 0.5
    assert result.summary["recall_at_k"] == 0.5
    assert len(result.items) == 2
