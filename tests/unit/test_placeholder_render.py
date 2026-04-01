from src.placeholder_render import get_image_registry_from_graph_state, render_image_placeholders


class _Snapshot:
    def __init__(self, values):
        self.values = values


class _GraphOK:
    def __init__(self, values):
        self._values = values

    def get_state(self, _config):
        return _Snapshot(self._values)


class _GraphErr:
    def get_state(self, _config):
        raise RuntimeError("boom")


def test_render_image_placeholders_replaces_known_placeholder():
    text = "步骤如下：[[IMG:models-version:1]]"
    registry = {"[[IMG:models-version:1]]": "https://resouces.modelscope.cn/a.png"}

    rendered = render_image_placeholders(text, registry)

    assert "![相关截图](https://resouces.modelscope.cn/a.png)" in rendered


def test_render_image_placeholders_keeps_unknown_placeholder():
    text = "占位符：[[IMG:models-version:9]]"

    rendered = render_image_placeholders(text, {})

    assert rendered == text


def test_get_image_registry_from_graph_state_returns_mapping():
    graph = _GraphOK({"image_registry": {"[[IMG:doc:1]]": "https://x/a.png", "bad": ""}})

    mapping = get_image_registry_from_graph_state(graph, {"configurable": {"thread_id": "t1"}})

    assert mapping == {"[[IMG:doc:1]]": "https://x/a.png"}


def test_get_image_registry_from_graph_state_handles_errors():
    graph = _GraphErr()

    mapping = get_image_registry_from_graph_state(graph, {"configurable": {"thread_id": "t1"}})

    assert mapping == {}
