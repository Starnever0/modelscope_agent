import re
from typing import Any


IMG_PLACEHOLDER_PATTERN = re.compile(r"\[\[IMG:[^:\]]+:[^\]]+\]\]")


def render_image_placeholders(text: str, image_registry: dict[str, str] | None) -> str:
    if not text:
        return text

    registry = image_registry or {}

    def _replace(match: re.Match[str]) -> str:
        placeholder = match.group(0)
        url = registry.get(placeholder)
        if not url:
            return placeholder
        return f"![相关截图]({url})"

    return IMG_PLACEHOLDER_PATTERN.sub(_replace, text)


def get_image_registry_from_graph_state(graph: Any, config: dict) -> dict[str, str]:
    try:
        snapshot = graph.get_state(config)
    except Exception:
        return {}

    values = getattr(snapshot, "values", None)
    if not isinstance(values, dict):
        return {}

    registry = values.get("image_registry")
    if not isinstance(registry, dict):
        return {}

    return {str(k): str(v) for k, v in registry.items() if isinstance(v, str) and v.strip()}
