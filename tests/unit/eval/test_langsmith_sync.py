from types import SimpleNamespace

from src.eval.langsmith_sync import (
    configure_langsmith_tracing,
    run_langsmith_evaluation,
    upload_cases_to_langsmith,
)
from src.eval.types import EvalCase


class _FakeClient:
    def __init__(self):
        self.created_examples = None

    def list_datasets(self, dataset_name: str):
        return [SimpleNamespace(id="ds-1", name=dataset_name)]

    def create_dataset(self, dataset_name: str, description: str):
        return SimpleNamespace(id="ds-created", name=dataset_name)

    def list_examples(self, dataset_id: str, limit: int = 100):
        return [SimpleNamespace(inputs={"case_id": "existing"})]

    def create_examples(self, inputs, outputs, metadata, dataset_id: str):
        self.created_examples = {
            "inputs": inputs,
            "outputs": outputs,
            "metadata": metadata,
            "dataset_id": dataset_id,
        }


def test_configure_langsmith_tracing_sets_env(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    configure_langsmith_tracing(enabled=True, project="rag-eval")

    assert configure_langsmith_tracing(enabled=False) is False


def test_upload_cases_to_langsmith_skips_existing_case_ids():
    cases = [
        EvalCase(case_id="existing", query="q1", difficulty="easy"),
        EvalCase(case_id="new", query="q2", difficulty="easy"),
    ]
    cli = _FakeClient()

    dataset_id = upload_cases_to_langsmith("demo", cases, client=cli)

    assert dataset_id == "ds-1"
    assert cli.created_examples is not None
    assert len(cli.created_examples["inputs"]) == 1
    assert cli.created_examples["inputs"][0]["case_id"] == "new"


def test_run_langsmith_evaluation_calls_evaluate(monkeypatch):
    class _FakeResults:
        experiment_name = "exp-123"

    called = {}

    def _fake_evaluate(target, **kwargs):
        called["target"] = target
        called["kwargs"] = kwargs
        return _FakeResults()

    monkeypatch.setattr("src.eval.langsmith_sync._require_evaluate", lambda: _fake_evaluate)
    monkeypatch.setattr("src.eval.langsmith_sync._require_client", lambda: lambda: _FakeClient())

    def _target(inputs):
        return {"answer": "ok", "retrieved_docids": []}

    exp_name = run_langsmith_evaluation(
        dataset_name="demo_ds",
        target_fn=_target,
        experiment_prefix="ms-rag",
        metadata={"from": "unit-test"},
    )

    assert exp_name == "exp-123"
    assert called["kwargs"]["data"] == "demo_ds"
    assert called["kwargs"]["experiment_prefix"] == "ms-rag"
    assert len(called["kwargs"]["evaluators"]) == 2
