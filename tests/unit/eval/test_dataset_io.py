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


def test_load_eval_cases_requires_expected_docids(tmp_path):
    f = tmp_path / "bad.jsonl"
    line = {
        "case_id": "c1",
        "query": "如何下载模型",
        "expected_docids": [],
        "difficulty": "easy",
    }
    f.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_eval_cases_from_jsonl(str(f))


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
