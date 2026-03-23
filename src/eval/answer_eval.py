from difflib import SequenceMatcher
from typing import Dict, List

from src.eval.types import EvalCase, EvalItemResult, EvalResult


def text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def evaluate_text_similarity(
    cases: List[EvalCase],
    answers_by_case_id: Dict[str, str],
) -> EvalResult:
    items: List[EvalItemResult] = []

    for case in cases:
        answer = answers_by_case_id.get(case.case_id, "")
        if not case.reference_answer:
            items.append(
                EvalItemResult(
                    case_id=case.case_id,
                    metrics={"text_similarity": 0.0},
                    extra={"skipped": True, "reason": "missing_reference_answer"},
                )
            )
            continue

        sim = text_similarity(answer, case.reference_answer)
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics={"text_similarity": sim},
                extra={"skipped": False},
            )
        )

    valid = [i for i in items if not i.extra.get("skipped")]
    count = max(len(valid), 1)
    summary = {
        "text_similarity": round(sum(i.metrics["text_similarity"] for i in valid) / count, 6),
        "evaluated_count": float(len(valid)),
        "skipped_count": float(len(items) - len(valid)),
    }
    return EvalResult(items=items, summary=summary)
