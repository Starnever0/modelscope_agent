import json
from pathlib import Path
from typing import List

from src.eval.types import EvalCase


_ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}


def _validate_case(raw: dict, line_no: int) -> EvalCase:
    case_id = str(raw.get("case_id", "")).strip()
    query = str(raw.get("query", "")).strip()
    expected_docids = raw.get("expected_docids")
    difficulty = str(raw.get("difficulty", "easy")).strip().lower()

    if not case_id:
        raise ValueError(f"Line {line_no}: case_id is required")
    if not query:
        raise ValueError(f"Line {line_no}: query is required")
    if not isinstance(expected_docids, list) or not expected_docids:
        raise ValueError(f"Line {line_no}: expected_docids must be a non-empty list")
    if difficulty not in _ALLOWED_DIFFICULTY:
        raise ValueError(f"Line {line_no}: difficulty must be one of {_ALLOWED_DIFFICULTY}")

    return EvalCase(
        case_id=case_id,
        query=query,
        expected_docids=[str(x) for x in expected_docids],
        reference_answer=raw.get("reference_answer"),
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
