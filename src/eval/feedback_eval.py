from typing import List

from src.eval.types import EvalCase, EvalItemResult, EvalResult


def evaluate_feedback(cases: List[EvalCase]) -> EvalResult:
    items: List[EvalItemResult] = []

    for case in cases:
        rating = case.user_rating
        has_feedback = bool((case.user_feedback or "").strip())
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics={
                    "user_rating": float(rating) if rating is not None else 0.0,
                    "has_feedback": 1.0 if has_feedback else 0.0,
                },
                extra={"dataset_type": case.dataset_type, "skipped": rating is None},
            )
        )

    with_rating = [i for i in items if not i.extra.get("skipped")]
    rating_count = max(len(with_rating), 1)
    summary = {
        "avg_user_rating": round(sum(i.metrics["user_rating"] for i in with_rating) / rating_count, 6),
        "feedback_coverage": round(sum(i.metrics["has_feedback"] for i in items) / max(len(items), 1), 6),
        "evaluated_count": float(len(with_rating)),
        "total_count": float(len(items)),
    }
    return EvalResult(items=items, summary=summary)
