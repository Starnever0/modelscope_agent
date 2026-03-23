from src.eval.answer_eval import evaluate_text_similarity, text_similarity
from src.eval.types import EvalCase


def test_text_similarity_basic():
    assert text_similarity("abc", "abc") == 1.0
    assert text_similarity("abc", "xyz") < 1.0


def test_evaluate_text_similarity_skips_missing_reference():
    cases = [
        EvalCase(case_id="c1", query="q1", expected_docids=[], reference_answer=None, difficulty="easy"),
        EvalCase(case_id="c2", query="q2", expected_docids=[], reference_answer="标准答案", difficulty="easy"),
    ]
    answers = {"c1": "回答1", "c2": "标准答案"}
    result = evaluate_text_similarity(cases, answers)
    assert result.summary["evaluated_count"] == 1.0
    assert result.summary["skipped_count"] == 1.0
