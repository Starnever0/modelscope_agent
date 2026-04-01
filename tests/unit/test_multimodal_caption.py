from src.multimodal.caption import _normalize_caption_text, build_caption_prompt, build_fallback_caption


def test_normalize_caption_text_from_string():
    assert _normalize_caption_text("  一段描述  ") == "一段描述"


def test_normalize_caption_text_from_list():
    content = [
        {"type": "text", "text": "第一句"},
        {"type": "text", "text": "第二句"},
    ]
    assert _normalize_caption_text(content) == "第一句 第二句"


def test_build_fallback_caption_with_alt():
    assert "截图" in build_fallback_caption("截图")


def test_build_fallback_caption_without_alt():
    assert build_fallback_caption("") == "文档配图，建议结合上下文理解。"


def test_build_caption_prompt_contains_alt_and_context():
    prompt = build_caption_prompt(alt_text="截图", context_text="通过页面设置模型版本")

    assert "【图片 alt】截图" in prompt
    assert "【上下文片段】通过页面设置模型版本" in prompt
    assert "不得臆测" in prompt
    assert "按钮名、字段名、参数名" in prompt
    assert "只输出纯文本一句话" in prompt
