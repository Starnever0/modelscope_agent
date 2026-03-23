from src.eval.feedback_eval import evaluate_feedback
from src.eval.types import EvalCase


def test_feedback_eval_summary():
    cases = [
        EvalCase(case_id="f1", query="q1", dataset_type="feedback", bot_answer="a1", user_rating=4.0, user_feedback="好", difficulty="easy"),
        EvalCase(case_id="f2", query="q2", dataset_type="feedback", bot_answer="a2", user_rating=2.0, user_feedback="", difficulty="easy"),
    ]
    result = evaluate_feedback(cases)
    assert result.summary["avg_user_rating"] == 3.0
    assert result.summary["feedback_coverage"] == 0.5
