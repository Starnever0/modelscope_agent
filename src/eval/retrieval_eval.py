from typing import Callable, List

from src.eval.types import EvalCase, EvalItemResult, EvalResult


def hit_at_k(expected_docids: List[str], predicted_docids: List[str], k: int) -> float:
    topk = set(predicted_docids[:k])
    return 1.0 if any(docid in topk for docid in expected_docids) else 0.0


def recall_at_k(expected_docids: List[str], predicted_docids: List[str], k: int) -> float:
    if not expected_docids:
        return 0.0
    topk = set(predicted_docids[:k])
    matched = sum(1 for docid in expected_docids if docid in topk)
    return matched / len(expected_docids)


def mrr_at_k(expected_docids: List[str], predicted_docids: List[str], k: int) -> float:
    expected = set(expected_docids)
    for idx, docid in enumerate(predicted_docids[:k], start=1):
        if docid in expected:
            return 1.0 / idx
    return 0.0


def evaluate_retrieval(
    cases: List[EvalCase],
    retrieve_docids_fn: Callable[[str, int], List[str]],
    k: int = 10,
) -> EvalResult:
    items: List[EvalItemResult] = []

    for case in cases:
        predicted = retrieve_docids_fn(case.query, k)
        metrics = {
            "hit_at_k": hit_at_k(case.expected_docids, predicted, k),
            "recall_at_k": recall_at_k(case.expected_docids, predicted, k),
            "mrr_at_k": mrr_at_k(case.expected_docids, predicted, k),
        }
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics=metrics,
                extra={"predicted_docids": predicted[:k]},
            )
        )

    count = max(len(items), 1)
    summary = {
        "hit_at_k": sum(i.metrics["hit_at_k"] for i in items) / count,
        "recall_at_k": sum(i.metrics["recall_at_k"] for i in items) / count,
        "mrr_at_k": sum(i.metrics["mrr_at_k"] for i in items) / count,
    }
    return EvalResult(items=items, summary=summary)
