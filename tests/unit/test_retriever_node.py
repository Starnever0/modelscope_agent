from langchain_core.documents import Document

from src.node import retriever


class _FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def invoke(self, query: str):
        self.queries.append(query)
        return self.docs


def test_retrieve_docs_node_limits_simple_query_docs_and_logs_count(monkeypatch, capsys):
    docs = [Document(page_content=f"doc-{i}") for i in range(8)]
    fake_retriever = _FakeRetriever(docs)
    monkeypatch.setattr(retriever, "get_cached_retriever", lambda _: fake_retriever)

    result = retriever.retrieve_docs_node({"rewritten_query": "简单问题"})

    assert fake_retriever.queries == ["简单问题"]
    assert len(result["retrieved_docs"]) == 5
    assert [d.page_content for d in result["retrieved_docs"]] == [
        "doc-0",
        "doc-1",
        "doc-2",
        "doc-3",
        "doc-4",
    ]

    output = capsys.readouterr().out
    assert "简单检索命中" in output
    assert "传入生成" in output
    assert "8" in output
    assert "5" in output
