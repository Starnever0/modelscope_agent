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
    evaluated_count = 0

    for case in cases:
        # 无 expected_docids 的样本不参与召回评估（可继续用于延迟与生成质量评估）
        if not case.expected_docids:
            items.append(
                EvalItemResult(
                    case_id=case.case_id,
                    metrics={
                        "hit_at_k": 0.0,
                        "recall_at_k": 0.0,
                        "mrr_at_k": 0.0,
                    },
                    extra={"skipped": True, "reason": "missing_expected_docids"},
                )
            )
            continue

        predicted = retrieve_docids_fn(case.query, k)
        metrics = {
            "hit_at_k": hit_at_k(case.expected_docids, predicted, k),
            "recall_at_k": recall_at_k(case.expected_docids, predicted, k),
            "mrr_at_k": mrr_at_k(case.expected_docids, predicted, k),
        }
        evaluated_count += 1
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics=metrics,
                extra={"predicted_docids": predicted[:k]},
            )
        )

    count = max(evaluated_count, 1)
    summary = {
        "hit_at_k": round(sum(i.metrics["hit_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "recall_at_k": round(sum(i.metrics["recall_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "mrr_at_k": round(sum(i.metrics["mrr_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "evaluated_count": float(evaluated_count),
        "skipped_count": float(len(items) - evaluated_count),
    }
    return EvalResult(items=items, summary=summary)
