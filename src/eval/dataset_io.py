"""
Dataset loading and validation for evaluation cases.
"""
import json
from pathlib import Path
from typing import List

from src.eval.types import EvalCase


_ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}
_ALLOWED_DATASET_TYPE = {"qa", "feedback"}


def _validate_case(raw: dict, line_no: int) -> EvalCase:
    case_id = str(raw.get("case_id", "")).strip()
    query = str(raw.get("query", "")).strip()
    expected_docids = raw.get("expected_docids", [])
    difficulty = str(raw.get("difficulty", "easy")).strip().lower()
    dataset_type = str(raw.get("dataset_type", "qa")).strip().lower()
    reference_answer = raw.get("reference_answer")
    bot_answer = raw.get("bot_answer")
    user_rating = raw.get("user_rating")
    user_feedback = raw.get("user_feedback")

    if not case_id:
        raise ValueError(f"Line {line_no}: case_id is required")
    if not query:
        raise ValueError(f"Line {line_no}: query is required")
    if dataset_type not in _ALLOWED_DATASET_TYPE:
        raise ValueError(f"Line {line_no}: dataset_type must be one of {_ALLOWED_DATASET_TYPE}")
    if difficulty not in _ALLOWED_DIFFICULTY:
        raise ValueError(f"Line {line_no}: difficulty must be one of {_ALLOWED_DIFFICULTY}")

    if not isinstance(expected_docids, list):
        raise ValueError(f"Line {line_no}: expected_docids must be a list")

    if dataset_type == "feedback":
        if bot_answer is None:
            raise ValueError(f"Line {line_no}: feedback dataset requires bot_answer")
        if user_rating is not None:
            try:
                float(user_rating)
            except (TypeError, ValueError):
                raise ValueError(f"Line {line_no}: user_rating must be numeric when provided")

    return EvalCase(
        case_id=case_id,
        query=query,
        expected_docids=[str(x) for x in expected_docids],
        reference_answer=reference_answer,
        bot_answer=str(bot_answer) if bot_answer is not None else None,
        user_rating=float(user_rating) if user_rating is not None else None,
        user_feedback=str(user_feedback) if user_feedback is not None else None,
        dataset_type=dataset_type,
        tags=[str(x) for x in raw.get("tags", [])],
        difficulty=difficulty,
        metadata=raw.get("metadata", {}),
    )


def load_eval_cases_from_jsonl(path: str) -> List[EvalCase]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {path}")

    cases: List[EvalCase] = []
    with file_path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            cases.append(_validate_case(raw, idx))

    if not cases:
        raise ValueError("Dataset is empty")

    return cases
