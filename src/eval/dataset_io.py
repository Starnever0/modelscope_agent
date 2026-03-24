"""
加载评测案例的工具函数，支持从 JSONL 文件中读取并验证数据格式，确保每个评测案例包含必要的字段和合理的值。
评测案例的字段包括：
- case_id: 唯一标识一个评测案例的字符串，必填。
- query: 评测问题或查询文本，必填。
- expected_docids: 与 query 相关的文档 ID 列表，用于检索评测，默认为空列表。
- reference_answer: 可选的参考答案文本，用于生成质量评测。
- bot_answer: 评测中生成的答案文本，主要用于反馈数据集。
- user_rating: 用户对 bot_answer 的评分，数值类型，主要用于反馈数据集。
- user_feedback: 用户对 bot_answer 的文字反馈，主要用于反馈数据集。
- dataset_type: 数据集类型，区分 "qa" 和 "feedback"，默认为 "qa"。
- tags: 评测案例的标签列表，默认为空列表。
- difficulty: 评测案例的难度级别，区分 "easy"、"medium" 和 "hard"，默认为 "easy"。
- metadata: 评测案例的元数据，用于存储额外的信息。
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
