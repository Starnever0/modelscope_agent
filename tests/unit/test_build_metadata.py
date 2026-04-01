from build import absolutize_markdown_image_links, build_docid, enrich_markdown_images, parse_metadata


def test_parse_metadata_extracts_docdata_url():
    text = (
        "> Source URL: https://modelscope.cn/docs/models/version\n"
        "> Title: 使用Library下载模型\n"
        "> Data Type: doc\n"
        "> DocData URL: https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/version_CN.md\n"
    )

    meta = parse_metadata(text, "version.md")

    assert meta["source_url"] == "https://modelscope.cn/docs/models/version"
    assert meta["docdata_url"] == (
        "https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/version_CN.md"
    )


def test_build_absolutize_markdown_image_links_prefers_docdata_url():
    text = "![截图](./_resources/model_version.png)"
    docdata_url = "https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/version_CN.md"
    source_url = "https://modelscope.cn/docs/models/version"

    updated = absolutize_markdown_image_links(text, docdata_url=docdata_url, source_url=source_url)

    assert (
        "https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/_resources/model_version.png"
        in updated
    )


def test_build_absolutize_markdown_image_links_falls_back_to_source_url():
    text = "![截图](./_resources/model_version.png)"
    source_url = "https://modelscope.cn/docs/models/version"

    updated = absolutize_markdown_image_links(text, docdata_url="", source_url=source_url)

    assert "https://modelscope.cn/docs/models/_resources/model_version.png" in updated


def test_build_docid_is_stable_by_source_url():
    meta = {"source_url": "https://modelscope.cn/docs/models/version"}

    docid_1 = build_docid(meta, "version.md")
    docid_2 = build_docid(meta, "version.md")

    assert docid_1 == docid_2
    assert docid_1.startswith("doc-")


def test_enrich_markdown_images_injects_placeholder_and_caption(monkeypatch):
    monkeypatch.setattr("build.ENABLE_IMAGE_CAPTION", True)
    monkeypatch.setattr(
        "build.generate_image_caption",
        lambda image_url, alt_text, context_text: f"caption:{alt_text}:{image_url}:{'ctx' if context_text else 'noctx'}",
    )

    docid = "doc-abc"
    text = "前文\n![截图](https://resouces.modelscope.cn/a.png)\n后文"

    enriched, image_map = enrich_markdown_images(text, docid)

    assert "[[IMG:doc-abc:1]]" in enriched
    assert "caption:截图:https://resouces.modelscope.cn/a.png:ctx" in enriched
    assert image_map == {"1": "https://resouces.modelscope.cn/a.png"}
