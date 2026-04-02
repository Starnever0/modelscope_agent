import threading
import time

from langchain_core.documents import Document

from src.node import parallel_retrieve


class _FakeRetriever:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    def invoke(self, query: str):
        with self._lock:
            self.active += 1
            if self.active > self.max_active:
                self.max_active = self.active
        # Sleep makes overlap observable if calls run in parallel.
        time.sleep(0.05)
        with self._lock:
            self.active -= 1

        return [
            Document(page_content=f"shared-{query[0]}"),
            Document(page_content="shared"),
        ]


def test_parallel_retrieve_node_returns_existing_docs_when_no_sub_questions():
    docs = [Document(page_content="fallback")]
    state = {"sub_questions": [], "retrieved_docs": docs}

    result = parallel_retrieve.parallel_retrieve_node(state)

    assert result["all_retrieved_docs"] == docs


def test_parallel_retrieve_node_runs_sub_queries_in_parallel_and_deduplicates(monkeypatch):
    fake_retriever = _FakeRetriever()
    monkeypatch.setattr(parallel_retrieve, "get_cached_retriever", lambda _: fake_retriever)

    state = {
        "sub_questions": ["q1", "q2", "q3", "q4"],
        "retrieved_docs": [],
    }

    result = parallel_retrieve.parallel_retrieve_node(state)

    docs = result["all_retrieved_docs"]
    contents = [doc.page_content for doc in docs]

    # Serial execution keeps max_active at 1; true parallelism should exceed 1.
    assert fake_retriever.max_active > 1
    assert len(contents) == len(set(contents))
    assert "shared" in contents
