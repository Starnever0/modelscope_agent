from langchain_core.messages import HumanMessage

from src.llm.provider import get_multimodal_llm_for_scene
from src.prompt.caption_prompt import build_caption_prompt


def _normalize_caption_text(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return " ".join(parts).strip()

    return ""


def build_fallback_caption(alt_text: str) -> str:
    alt = (alt_text or "").strip()
    if alt:
        return f"图片内容与“{alt}”相关。"
    return "文档配图，建议结合上下文理解。"


def generate_image_caption(image_url: str, alt_text: str = "", context_text: str = "") -> str:
    if not image_url:
        return build_fallback_caption(alt_text)

    prompt = build_caption_prompt(alt_text=alt_text, context_text=context_text)

    try:
        llm = get_multimodal_llm_for_scene("image_caption")
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        )
        response = llm.invoke([message])
        text = _normalize_caption_text(getattr(response, "content", ""))
        if text:
            return text[:120]
    except Exception:
        pass

    return build_fallback_caption(alt_text)
