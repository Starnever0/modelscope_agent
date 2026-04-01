from crawl.crawl import absolutize_markdown_image_links


def test_absolutize_image_links_prefers_docdata_url_base():
    markdown = "![截图](./_resources/model_version.png)"
    docdata_url = "https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/version_CN.md"
    source_url = "https://modelscope.cn/docs/models/version"

    updated = absolutize_markdown_image_links(markdown, docdata_url=docdata_url, source_url=source_url)

    assert (
        "https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/version/_resources/model_version.png"
        in updated
    )


def test_absolutize_image_links_falls_back_to_source_url():
    markdown = "![截图](./_resources/model_version.png)"
    source_url = "https://modelscope.cn/docs/models/version"

    updated = absolutize_markdown_image_links(markdown, docdata_url="", source_url=source_url)

    assert "https://modelscope.cn/docs/models/_resources/model_version.png" in updated


def test_absolutize_image_links_keeps_absolute_url_unchanged():
    markdown = "![截图](https://example.com/static/a.png)"

    updated = absolutize_markdown_image_links(markdown, docdata_url="", source_url="https://modelscope.cn/docs/models/version")

    assert updated == markdown


def test_absolutize_image_links_does_not_change_normal_links():
    markdown = "[文档](./quick-start.md)"

    updated = absolutize_markdown_image_links(markdown, docdata_url="", source_url="https://modelscope.cn/docs/models/version")

    assert updated == markdown
