from types import SimpleNamespace

from langchain_core.documents import Document

from src.node import generate


class _DummyChain:
    def __init__(self):
        self.last_payload = None

    def invoke(self, payload):
        self.last_payload = payload
        return SimpleNamespace(content="ok")


def test_generate_node_injects_placeholders_and_registry(monkeypatch):
    dummy_chain = _DummyChain()
    monkeypatch.setattr(generate, "generate_chain", dummy_chain)

    docs = [
        Document(
            page_content="模型版本说明",
            metadata={
                "source_url": "https://modelscope.cn/docs/models/version",
                "docid": "models-version",
                "image_map": {"1": "https://resouces.modelscope.cn/a.png"},
            },
        )
    ]
    state = {
        "messages": [SimpleNamespace(content="如何设置模型版本")],
        "retrieved_docs": docs,
    }

    result = generate.generate_node(state)

    assert "[[IMG:models-version:1]]" in result["context"]
    assert result["image_registry"] == {"[[IMG:models-version:1]]": "https://resouces.modelscope.cn/a.png"}
    assert "[[IMG:models-version:1]]" in dummy_chain.last_payload["context"]


def test_generate_node_supports_list_image_map(monkeypatch):
    dummy_chain = _DummyChain()
    monkeypatch.setattr(generate, "generate_chain", dummy_chain)

    docs = [
        Document(
            page_content="图文教程",
            metadata={
                "source_url": "https://modelscope.cn/docs/models/version",
                "image_map": [{"idx": 2, "url": "https://resouces.modelscope.cn/b.png"}],
            },
        )
    ]
    state = {
        "messages": [SimpleNamespace(content="给我图文教程")],
        "retrieved_docs": docs,
    }

    result = generate.generate_node(state)

    placeholder = next(iter(result["image_registry"].keys()))
    assert placeholder.endswith(":2]]")
    assert result["image_registry"][placeholder] == "https://resouces.modelscope.cn/b.png"


def test_generate_node_web_answer_returns_empty_registry(monkeypatch):
    dummy_chain = _DummyChain()
    monkeypatch.setattr(generate, "generate_chain", dummy_chain)

    state = {
        "messages": [SimpleNamespace(content="最新公告")],
        "web_answer": "web context",
        "retrieved_docs": [],
    }

    result = generate.generate_node(state)

    assert result["context"] == "web context"
    assert result["image_registry"] == {}
