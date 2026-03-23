import json
from typing import Callable, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from src.eval.types import EvalCase, EvalItemResult, EvalResult
from src.llm.provider import get_normal_llm_for_scene


JudgeFn = Callable[[str, str, Optional[str]], Dict[str, float]]


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_llm_judge() -> JudgeFn:
    llm = get_normal_llm_for_scene("eval_judge")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an evaluator for RAG answers.
Score three dimensions from 0.0 to 1.0:
1) relevance
2) groundedness
3) completeness
Return strict JSON with keys: relevance, groundedness, completeness, reason.
""".strip(),
            ),
            (
                "human",
                "Query: {query}\nReference: {reference}\nAnswer: {answer}",
            ),
        ]
    )
    chain = prompt | llm

    def judge(query: str, answer: str, reference: Optional[str]) -> Dict[str, float]:
        resp = chain.invoke(
            {
                "query": query,
                "answer": answer,
                "reference": reference or "",
            }
        )
        content = getattr(resp, "content", "")
        try:
            data = json.loads(content)
        except Exception:
            data = {
                "relevance": 0.0,
                "groundedness": 0.0,
                "completeness": 0.0,
                "reason": "invalid_json_from_judge",
            }

        return {
            "relevance": _safe_float(data.get("relevance")),
            "groundedness": _safe_float(data.get("groundedness")),
            "completeness": _safe_float(data.get("completeness")),
            "reason": str(data.get("reason", "")),
        }

    return judge


def evaluate_judge(
    cases: List[EvalCase],
    answers_by_case_id: Dict[str, str],
    judge_fn: JudgeFn,
) -> EvalResult:
    items: List[EvalItemResult] = []

    for case in cases:
        answer = answers_by_case_id.get(case.case_id, "")
        raw = judge_fn(case.query, answer, case.reference_answer)
        relevance = _safe_float(raw.get("relevance"))
        groundedness = _safe_float(raw.get("groundedness"))
        completeness = _safe_float(raw.get("completeness"))
        overall = (relevance + groundedness + completeness) / 3.0
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics={
                    "relevance": relevance,
                    "groundedness": groundedness,
                    "completeness": completeness,
                    "judge_score": overall,
                },
                extra={"reason": raw.get("reason", "")},
            )
        )

    count = max(len(items), 1)
    summary = {
        "relevance": round(sum(i.metrics["relevance"] for i in items) / count, 6),
        "groundedness": round(sum(i.metrics["groundedness"] for i in items) / count, 6),
        "completeness": round(sum(i.metrics["completeness"] for i in items) / count, 6),
        "judge_score": round(sum(i.metrics["judge_score"] for i in items) / count, 6),
    }
    return EvalResult(items=items, summary=summary)
