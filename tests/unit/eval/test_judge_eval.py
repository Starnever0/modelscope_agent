from src.eval.judge_eval import evaluate_judge
from src.eval.types import EvalCase


def test_judge_eval_aggregate():
    cases = [
        EvalCase(case_id="c1", query="q1", expected_docids=["d1"], reference_answer="a1", difficulty="easy"),
        EvalCase(case_id="c2", query="q2", expected_docids=["d2"], reference_answer="a2", difficulty="easy"),
    ]

    answers = {"c1": "ans1", "c2": "ans2"}

    def judge_fn(_q, _a, _r):
        return {"relevance": 0.8, "groundedness": 0.7, "completeness": 0.9, "reason": "ok"}

    result = evaluate_judge(cases, answers, judge_fn)
    assert len(result.items) == 2
    assert result.summary["judge_score"] == 0.8
