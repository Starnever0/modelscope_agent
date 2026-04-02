from types import SimpleNamespace

from langchain_core.documents import Document

from src.node import grade_doc


class _ShouldNotBeCalledChain:
    def invoke(self, _payload):
        raise AssertionError("grade_chain.invoke should not be called")


def test_grade_node_skips_llm_when_no_docs_and_first_try(monkeypatch):
    monkeypatch.setattr(grade_doc, "grade_chain", _ShouldNotBeCalledChain())

    state = {
        "rewritten_query": "如何部署模型",
        "retrieved_docs": [],
        "loop_step": 0,
    }

    assert grade_doc.grade_node(state) == "rewrite_node"


def test_grade_node_sends_compact_document_text_to_chain(monkeypatch):
    captured = {}

    class _DummyChain:
        def invoke(self, payload):
            captured["payload"] = payload
            return SimpleNamespace(binary_score="yes")

    monkeypatch.setattr(grade_doc, "grade_chain", _DummyChain())

    docs = [
        Document(page_content="A" * 2000, metadata={"source_url": "u1"}),
        Document(page_content="B" * 2000, metadata={"source_url": "u2"}),
        Document(page_content="C" * 2000, metadata={"source_url": "u3"}),
        Document(page_content="D" * 2000, metadata={"source_url": "u4"}),
    ]

    state = {
        "rewritten_query": "如何部署模型",
        "retrieved_docs": docs,
        "loop_step": 0,
    }

    result = grade_doc.grade_node(state)

    assert result == "generator_node"
    assert isinstance(captured["payload"]["documents"], str)
    assert "文档1" in captured["payload"]["documents"]
    assert "文档2" in captured["payload"]["documents"]
    assert "文档3" in captured["payload"]["documents"]
    assert "文档4" not in captured["payload"]["documents"]
    assert len(captured["payload"]["documents"]) < 5000
