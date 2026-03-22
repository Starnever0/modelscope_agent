# Crawl Spec: ModelScope 文档中心抓取规范

## 1. 背景与目标

本项目目标是抓取魔搭社区文档中心 `https://modelscope.cn/docs/` 下的文档正文内容，并保存为 Markdown 文件用于后续知识库构建。

关键要求：

1. 仅抓取文档正文，不包含导航栏、页脚、分享区等无关元素。
2. 仅覆盖文档中心页面（`/docs/` 前缀）。
3. 每个文档页面应映射到对应的 docdata CN Markdown 资源并抓取。
4. 先完成“全量页面链接发现”，再进行“逐页 md 资源映射与下载”。

首页入口：

- `https://modelscope.cn/docs/home`

典型页面：

- `https://modelscope.cn/docs/intro/quickstart`
- `https://modelscope.cn/docs/models/download`
- `https://modelscope.cn/docs/llm-training-and-inference/intro/swift-installation`

典型资源（示例）：

- `https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/intro/quickstart/quickstart_CN.md`

## 2. 范围定义

### 2.1 In Scope

1. `https://modelscope.cn/docs/` 下所有文档页面的 URL 发现与去重。
2. docs 页面到 docdata CN Markdown 的映射。
3. Markdown 正文抓取与本地存储。
4. 抓取过程中的状态记录、映射记录、失败记录。

### 2.2 Out of Scope

1. `https://modelscope.cn/learn`、`/models`、`/datasets`、`/studios`、`/mcp`、`/aigc` 等非 docs 页面。
2. GitHub 文档抓取。
3. 图片、二进制资源、附件文件抓取。
4. 页面视觉元素抓取（导航、页脚、分享按钮等）。

## 3. 核心流程（两阶段）

### 阶段 A：发现所有 docs 页面链接

目标：得到“文档中心有哪些文档页面”的完整 URL 集合。

输入：

- `https://modelscope.cn/docs/home`

规则：

1. 只保留 `https://modelscope.cn/docs/` 前缀 URL。
2. 统一 URL 归一化（域名、尾斜杠、fragment 清理）。
3. 去重并记录来源页面（可追溯）。
4. 对非文档链接（协议、社媒、资源文件）进行过滤。

产出：

- docs 原始页面列表（用于后续映射）：`data/docs_links_index.json`

推荐实现（主流程）：

1. 优先请求 `https://resouces.modelscope.cn/document/docdata/<version>/dist/title-mapping.json`。
2. 读取其中所有 value 路径（如 `intro/quickstart`、`models/download`）。
3. 拼接为 docs 原网址：`https://modelscope.cn/docs/<value>`。
4. 对拼接结果应用 URL 合法性过滤（仅 https、仅 modelscope.cn、仅 /docs、仅 ASCII slug、非资源路径）。
5. 将过滤后的链接写入 `data/docs_links_index.json` 作为主要发现结果。

说明：

- `title-mapping.json` 作为文档目录映射主数据源，覆盖率高于仅依赖页面导航抓取。
- 页面导航抓取可作为补充发现来源，但不得覆盖或污染主来源结果。

### 阶段 B：映射并抓取 docdata CN Markdown

对阶段 A 得到的每个 docs URL 执行映射，优先抓取官方 docdata CN Markdown。

映射思路：

1. 将 docs URL 的路径（去掉 `/docs/` 前缀）拆分为路由段。
2. 基于路由段构造 docdata 候选路径（多规则尝试）。
3. 命中 200 且内容有效时，作为该页面正文来源。
4. 若多个候选命中，选择与页面 slug 语义最接近且正文有效的版本。

示例：

- docs URL: `https://modelscope.cn/docs/intro/quickstart`
- 目标 md: `https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/intro/quickstart/quickstart_CN.md`

- docs URL: `https://modelscope.cn/docs/models/advanced-usage/ollama-integration`
- 目标 md: `https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/models/advanced-usage/ollama-integration/ollama-integration_CN.md`
  
## 4. URL 与文件命名规范

### 4.1 建议存储结构（优先）

按 docs 路径分层存储，保持可读性和可维护性。

示例：

- docs URL: `/docs/llm-training-and-inference/intro/swift-installation`
- 本地文件: `data/raw/docs/llm-training-and-inference/intro/swift-installation.md`

### 4.2 备选命名（单文件扁平）

若某些场景不便于多级目录，可使用下划线扁平命名：

- `llm-training-and-inference_intro_swift-installation.md`

默认采用 4.1 多级目录方式。

## 5. 输出与状态文件

### 5.1 文档正文输出

- 根目录：`data/raw/docs/`
- 编码：UTF-8
- 内容：正文 Markdown（不带导航、页脚）

### 5.2 映射与索引输出

建议维护以下文件：

1. `data/docs_links_index.json`
2. `data/docs_url_to_md_map.json`
3. `data/docs_fetch_report.json`

字段建议：

1. docs_url
2. docdata_url
3. status（mapped/fetched/failed）
4. reason（失败原因）
5. updated_at

## 6. 质量要求

1. 正文纯度：不得包含导航菜单、协议链接区、社媒链接区。
2. 覆盖率：应尽可能覆盖 docs 全量页面；失败项必须有记录。
3. 可复现：同一版本 docdata 下，多次抓取结果稳定。
4. 可增量：支持按状态文件增量更新，不重复抓取未变更页面。

## 7. 错误处理与降级策略

1. 单页映射失败不应中断全局流程。
2. 失败页面写入失败报告，包含 URL 与错误原因。
3. 对网络抖动采用重试策略（有限次数）。
4. docdata 版本更新时，应支持通过配置切换版本目录。

## 8. 配置项

建议保留以下可配置参数：

1. `MODELSCOPE_DOCS_DOCDATA_VERSION`（例如 `2026-3-17_11-15-CN`）
2. 请求超时（秒）
3. 最大页面数
4. 最大发现深度
5. 重试次数

## 9. 验收标准

满足以下条件即可验收：

1. 能从 `https://modelscope.cn/docs/home` 发现 docs 页面链接并落盘。
2. 能将发现到的 docs 页面批量映射到 docdata CN Markdown。
3. 抓取结果保存为本地 Markdown，目录结构可读。
4. 示例页面可稳定命中：
   - `/docs/models/upload`
   - `/docs/models/download`
   - `/docs/intro/quickstart`
   - `/docs/llm-training-and-inference/intro/swift-installation`
5. 失败页面可追踪（失败原因明确）。

## 10. 后续开发约束

后续所有爬虫改动需遵循本规范：

1. 先完善链接发现，再完善映射规则。
2. 优先保证正文质量，其次追求覆盖率。
3. 每次改动后更新映射报告和失败报告，便于维护。

## 11. 问题记录与修复约束

### 11.1 已发现问题

`data/docs_links_index.json` 曾出现大量无效链接，例如：

1. `blob://http://localhost/...`（浏览器临时对象 URL）
2. `http://your_user_name@modelscope.ai':/`（示例字符串误识别）
3. `https://modelscope.cn/docs/%E5%B8%B8...`（中文路径编码，不是规范文档路由）
4. `https://modelscope.cn/docs/datasets/_resources/restricted_dataset.png`（静态资源）

### 11.2 修复要求（强约束）

写入 docs 链接索引和映射流程的 URL，必须满足以下条件：

1. 仅允许 `https` 协议。
2. 域名必须是 `modelscope.cn`。
3. 路径必须在 docs 前缀下：`/docs` 或 `/docs/...`。
4. docs 路由段必须是 ASCII slug（英数、`-`、`_`），不允许中文路径。
5. 排除静态资源路径（如 `/_resources/`）和资源后缀（png/jpg/svg/pdf/zip/md 等）。

不满足以上任一条件的链接不得进入：

1. `data/docs_links_index.json`
2. `data/docs_url_to_md_map.json`
3. 后续 docdata 映射队列

## 12. 最新问题与记录（持续更新）

### 12.1 本轮新增问题

1. title-mapping 中存在目录聚合路由（如 `/docs/models`、`/docs/model-evaluation/user-guides`），这些路由通常不对应独立 docdata 正文 md。
2. title-mapping 中存在少量孤儿路由（路由存在于映射表，但 docdata 下无可用 md）。
3. 页面发现链路可能补充出非权威路由（例如 `/docs/openapi`），这类路由不一定在 title-mapping 中，也不一定存在 docdata。

### 12.2 处理策略（已执行）

1. 对“目录聚合路由 + 无 docdata”的情况，状态记为 `skipped`，原因记为 `index_node_no_docdata`。
2. 对“仅来自 title-mapping 且无 docdata”的孤儿路由，状态记为 `skipped`，原因记为 `title_mapping_orphan`。
3. 对“来自页面发现但不在 title-mapping 且无 docdata”的路由，状态记为 `skipped`，原因记为 `discovered_unmapped`。
4. `failed` 仅保留真正异常（如网络错误、请求异常、应命中但未命中且无法归类的映射失败）。

### 12.3 报告字段约定（新增）

`data/docs_fetch_report.json` 中 `status` 与 `reason` 约定如下：

1. `fetched`: 成功映射并抓取 docdata。
2. `skipped`: 合法但无需视为错误的未命中路由。
3. `failed`: 需要修复或排查的真实错误。

### 12.4 当前基线（2026-03-22）

基于 docs-only 回归测试（title-mapping 主发现 + 页面发现补充）：

1. `fetched` 约 280+。
2. `skipped` 主要为目录页与孤儿路由。
3. `failed` 已降至极低数量（后续目标为仅保留真实异常）。

后续每次规则调整后，必须同步更新本节“新增问题、处理策略、基线结果”。
