"""LangSmith 数据集与结果同步工具。"""

from src.eval.types import EvalCase, EvalResult


def _require_client():
    try:
        from langsmith import Client
    except Exception as exc:
        raise RuntimeError("langsmith is not installed. Please add dependency 'langsmith'.") from exc
    return Client


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

    inputs = [
        {
            "query": c.query,
            "case_id": c.case_id,
            "tags": c.tags,
            "difficulty": c.difficulty,
            "dataset_type": c.dataset_type,
        }
        for c in cases
    ]
    outputs = [
        {
            "expected_docids": c.expected_docids,
            "reference_answer": c.reference_answer,
            "bot_answer": c.bot_answer,
            "user_rating": c.user_rating,
            "user_feedback": c.user_feedback,
        }
        for c in cases
    ]
    metadata = [c.metadata for c in cases]

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
