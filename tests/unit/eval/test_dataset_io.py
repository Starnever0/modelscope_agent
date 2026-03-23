import json

import pytest

from src.eval.dataset_io import load_eval_cases_from_jsonl


def test_load_eval_cases_success(tmp_path):
    f = tmp_path / "cases.jsonl"
    line = {
        "case_id": "c1",
        "query": "如何下载模型",
        "expected_docids": ["d1", "d2"],
        "reference_answer": "可用 SDK",
        "tags": ["download"],
        "difficulty": "easy",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    cases = load_eval_cases_from_jsonl(str(f))
    assert len(cases) == 1
    assert cases[0].case_id == "c1"


def test_load_eval_cases_allows_missing_expected_docids(tmp_path):
    f = tmp_path / "bad.jsonl"
    line = {
        "case_id": "c1",
        "query": "如何下载模型",
        "expected_docids": [],
        "difficulty": "easy",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    cases = load_eval_cases_from_jsonl(str(f))
    assert cases[0].expected_docids == []


def test_load_feedback_dataset_requires_bot_answer(tmp_path):
    f = tmp_path / "feedback_bad.jsonl"
    line = {
        "case_id": "fb1",
        "query": "怎么部署",
        "dataset_type": "feedback",
        "difficulty": "easy",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_eval_cases_from_jsonl(str(f))


def test_load_feedback_dataset_success(tmp_path):
    f = tmp_path / "feedback_ok.jsonl"
    line = {
        "case_id": "fb2",
        "query": "怎么下载模型",
        "bot_answer": "请用SDK下载",
        "user_rating": 4,
        "user_feedback": "还行",
        "dataset_type": "feedback",
        "difficulty": "easy",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    cases = load_eval_cases_from_jsonl(str(f))
    assert cases[0].dataset_type == "feedback"
    assert cases[0].bot_answer == "请用SDK下载"


def test_load_eval_cases_invalid_difficulty(tmp_path):
    f = tmp_path / "bad2.jsonl"
    line = {
        "case_id": "c1",
        "query": "如何下载模型",
        "expected_docids": ["d1"],
        "difficulty": "unknown",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_eval_cases_from_jsonl(str(f))
