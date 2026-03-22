# ModelScope Docs Crawler (精简使用说明)

本目录下爬虫用于抓取 ModelScope docs 正文 Markdown，采用两阶段流程：

1. 发现 docs 路由（title-mapping 为主，页面发现为辅）
2. 映射并抓取 docdata CN Markdown

## 1. 准备

在项目根目录执行：

```bash
uv sync
```

可选配置（.env）：

```env
MODELSCOPE_DOCS_DOCDATA_VERSION=2026-3-17_11-15-CN
```

## 2. 单次运行

在项目根目录执行：

```bash
uv run python crawl/crawl.py --sources docs --max-pages-per-source 500 --max-depth 4 --output-dir data/raw --reports-dir data --state-file data/crawl_state.json
```

## 3. 持续运行

```bash
uv run python crawl/crawl.py --sources docs --loop --interval-minutes 180 --output-dir data/raw --reports-dir data --state-file data/crawl_state.json
```

## 4. 结果位置

1. 正文文件：data/raw/docs/
2. 链接索引：data/docs_links_index.json
3. 映射关系：data/docs_url_to_md_map.json
4. 抓取报告：data/docs_fetch_report.json
5. 增量状态：data/crawl_state.json

## 5. 常用排查

1. docdata 版本不匹配：检查 MODELSCOPE_DOCS_DOCDATA_VERSION
2. 映射失败多：先看 data/docs_fetch_report.json 的 status 和 reason
3. 链接污染：先看 data/docs_links_index.json，确认是否含非 /docs 路由

详细规范见：crawl/crawl_spec.md
