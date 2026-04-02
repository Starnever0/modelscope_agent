"""LangSmith tracing、数据集与评测同步工具。"""

import os
from typing import Any, Callable

from src.eval.types import EvalCase, EvalResult


def _require_client():
    try:
        from langsmith import Client
    except Exception as exc:
        raise RuntimeError("langsmith is not installed. Please add dependency 'langsmith'.") from exc
    return Client


def _require_evaluate():
    try:
        from langsmith.evaluation import evaluate
    except Exception as exc:
        raise RuntimeError("langsmith evaluate is not available. Please ensure dependency 'langsmith' is installed.") from exc
    return evaluate


def configure_langsmith_tracing(enabled: bool, project: str | None = None) -> bool:
    """Enable LangSmith tracing through env vars for the current process."""
    if not enabled:
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project
    return True


def get_or_create_dataset_id(dataset_name: str, description: str = "RAG eval dataset", client=None) -> str:
    Client = _require_client()
    cli = client or Client()

    for ds in cli.list_datasets(dataset_name=dataset_name):
        return str(ds.id)

    created = cli.create_dataset(dataset_name=dataset_name, description=description)
    return str(created.id)


def upload_cases_to_langsmith(dataset_name: str, cases: list[EvalCase], client=None) -> str:
    Client = _require_client()
    cli = client or Client()
    dataset_id = get_or_create_dataset_id(dataset_name=dataset_name, client=cli)

    existing_case_ids = {
        str((example.inputs or {}).get("case_id", ""))
        for example in cli.list_examples(dataset_id=dataset_id, limit=10_000)
        if (example.inputs or {}).get("case_id")
    }
    new_cases = [c for c in cases if c.case_id not in existing_case_ids]

    if not new_cases:
        return dataset_id

    inputs = [
        {
            "query": c.query,
            "case_id": c.case_id,
            "tags": c.tags,
            "difficulty": c.difficulty,
            "dataset_type": c.dataset_type,
        }
        for c in new_cases
    ]
    outputs = [
        {
            "expected_docids": c.expected_docids,
            "reference_answer": c.reference_answer,
            "bot_answer": c.bot_answer,
            "user_rating": c.user_rating,
            "user_feedback": c.user_feedback,
        }
        for c in new_cases
    ]
    metadata = [c.metadata for c in new_cases]

    cli.create_examples(inputs=inputs, outputs=outputs, metadata=metadata, dataset_id=dataset_id)
    return dataset_id


def upload_result_summary(dataset_name: str, result_name: str, result: EvalResult, client=None) -> str:
    Client = _require_client()
    cli = client or Client()
    dataset_id = get_or_create_dataset_id(dataset_name=dataset_name, client=cli)
    cli.create_example(
        inputs={"type": "eval_summary", "result_name": result_name},
        outputs={"summary": result.summary},
        metadata={"source": "local_eval"},
        dataset_id=dataset_id,
    )
    return dataset_id


def run_langsmith_evaluation(
    dataset_name: str,
    target_fn: Callable[[dict[str, Any]], dict[str, Any]],
    experiment_prefix: str,
    metadata: dict[str, Any] | None = None,
    max_concurrency: int = 4,
    client=None,
) -> str:
    """Run LangSmith dataset evaluation against a target function."""
    Client = _require_client()
    evaluate = _require_evaluate()
    cli = client or Client()

    def reference_overlap_evaluator(run, example):
        outputs = run.outputs or {}
        example_outputs = (example.outputs or {}) if example else {}
        answer = str(outputs.get("answer") or "").strip()
        reference = str(example_outputs.get("reference_answer") or "").strip()
        if not reference:
            return {"key": "reference_overlap", "score": 0.0, "comment": "missing_reference_answer"}

        answer_tokens = {token for token in answer.split() if token}
        reference_tokens = {token for token in reference.split() if token}
        if not reference_tokens:
            return {"key": "reference_overlap", "score": 0.0, "comment": "empty_reference_answer"}

        overlap = len(answer_tokens & reference_tokens) / len(reference_tokens)
        return {"key": "reference_overlap", "score": float(overlap)}

    def retrieval_hit_evaluator(run, example):
        outputs = run.outputs or {}
        example_outputs = (example.outputs or {}) if example else {}
        expected_docids = set(example_outputs.get("expected_docids") or [])
        predicted_docids = set(outputs.get("retrieved_docids") or [])
        if not expected_docids:
            return {"key": "retrieval_hit", "score": 0.0, "comment": "missing_expected_docids"}

        score = 1.0 if expected_docids & predicted_docids else 0.0
        return {"key": "retrieval_hit", "score": score}

    results = evaluate(
        target_fn,
        data=dataset_name,
        evaluators=[reference_overlap_evaluator, retrieval_hit_evaluator],
        metadata=metadata or {},
        experiment_prefix=experiment_prefix,
        max_concurrency=max_concurrency,
        client=cli,
    )
    return str(getattr(results, "experiment_name", experiment_prefix))
