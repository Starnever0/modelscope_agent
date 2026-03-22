# ModelScope Agent SPEC

## 1. 文档目的

本 SPEC 用于持续维护以下内容：

- 当前项目已完成功能清单
- 当前系统边界与约束
- 迭代目标与验收标准
- 关键问题清单与处理状态

本文件会在每轮迭代后更新，并与更新日志联动。

## 1.1 开发范式（新增）

本项目从本轮开始采用 TDD（Test-Driven Development）范式，默认流程如下：

1. 先定义组件行为与验收条件
2. 先写失败测试（Red）
3. 实现最小可用代码使测试通过（Green）
4. 在不破坏行为的前提下重构（Refactor）

任何新增功能或重构应尽量满足：

- 组件有清晰输入输出与边界
- 组件可被独立测试（避免强耦合到 UI、网络或外部状态）
- 组件测试可单独运行（最小依赖、可重复）

## 2. 项目目标

构建一个面向 ModelScope 场景的问答 Agent，支持基于知识库的检索增强问答（RAG），并具备查询重写、文档评估、并行检索和重排序能力。

## 3. 当前架构与模块

- 入口与交互：Gradio Web 应用（app.py）
- 流程编排：LangGraph 状态图（src/graph.py）
- 模型配置中心：统一模型调用与模型名配置（src/llm/model_config.py）
- 检索体系：FAISS 向量检索 + BM25 关键词检索（src/node/retriever.py）
- 查询处理：Router、Query Decompose、Rewrite 节点
- 结果质量：Grade 节点、Rerank 节点
- 兜底能力：Web Search 节点（Tavily）
- 数据链路：crawl.py 抓取 Markdown 数据，build.py 构建向量索引

### 3.1 模块化约束（新增）

- 路由决策逻辑与图编排分离：决策函数放在独立模块，图文件只负责编排
- 数据持久化逻辑与界面事件分离：UI 事件层不直接处理文件读写
- 构建配置逻辑与构建执行分离：可测试的路径/配置函数独立于主流程

## 4. 已完成功能（截至 2026-03-22）

### 4.1 数据抓取

- 已支持多来源抓取与 Markdown 落盘
- docs 来源支持 docdata 优先、页面抓取回退
- 已完成本轮 docs 数据更新（data/raw/docs）

### 4.2 索引构建

- build.py 已支持递归读取 data/raw 子目录 Markdown
- 支持分块切分、元数据注入、FAISS 索引保存
- 支持批量失败后降级单条写入，具备一定容错能力

### 4.3 Agent 主流程

- Router：闲聊路径与文档问答路径路由
- Decompose：复杂查询拆分为子问题
- Parallel Retrieve：多子问题并行召回并去重
- Grade + Rewrite：文档质量判断与一次重写重试
- Rerank：候选文档重排序
- Generate：融合上下文生成最终回答

### 4.4 产品交互

- Gradio 聊天界面可启动
- 会话态维护（thread_id）
- 反馈按钮与反馈数据落盘

### 4.5 测试机制（新增）

- 单元测试框架：pytest（tests/unit）
- 已建立独立测试组件：
  - 路由决策组件测试
  - 构建目录解析组件测试
  - 反馈存储组件测试
- 测试运行基线：使用 uv 执行测试命令

### 4.6 模型调用治理（新增）

- 已将 Chat LLM、Embedding、Rerank 的模型名与调用入口统一到 `src/llm/model_config.py`
- 目标：后续更换模型时只需修改一个文件，降低多点改动风险

## 5. 运行基线（环境约定）

### 5.1 环境管理

- 项目标准运行环境为 uv
- Python 运行以 uv run 为准

### 5.2 标准命令

- 数据抓取：uv run python crawl.py
- 索引构建：uv run python build.py
- 启动应用：uv run python app.py

### 5.3 必要配置

- DASHSCOPE_API_KEY：必填（Embedding、LLM、Rerank）
- TAVILY_API_KEY：可选（Web 搜索兜底）

## 6. 首次任务：跑通整个项目

### 6.1 任务定义

“跑通”定义为以下步骤全部成功：

1. 基于最新抓取数据完成向量索引构建
2. 应用成功启动
3. 发起一次 docs 问答并返回可用答案

### 6.2 当前状态（2026-03-22）

- 已确认 uv 运行链路可用
- 已确认 app.py 可启动（Gradio 服务已拉起）
- 已修复 build.py 中未定义目录变量导致的构建启动失败问题
- 索引构建在 4603 个切片处理期间出现 DashScope `Arrearage` 错误，当前未产出 data/faiss_db
- 由于缺少最新 FAISS 索引，docs 问答链路尚未完成端到端验证

结论：首次“跑通整个项目”任务尚未完成。

### 6.3 当前主要阻塞

- 阻塞项 B1：DashScope Embedding API 返回 `Arrearage`，向量化请求被拒绝
- 阻塞影响：无法产出 data/faiss_db，检索链路不可用

## 7. 问题挖掘与迭代机制

后续每轮迭代按以下流程执行：

1. 记录问题：在本 SPEC 的问题列表新增条目
2. 制定修复：定义改动范围、风险、验收条件
3. 实施验证：执行命令并记录结果
4. 回写文档：更新 SPEC 状态和 CHANGELOG

## 8. 问题清单（持续更新）

### B1（高优先级）Embedding API 欠费阻塞

- 状态：Open
- 现象：uv run python build.py 向量化阶段反复返回 `status_code: 400 / code: Arrearage`
- 影响：无法生成 data/faiss_db，RAG 文档检索主路径不可用
- 下一步：
  - 确认 DashScope 账号可用额度与权限
  - 恢复后重新执行索引构建并校验向量库产物
  - 在完成后执行 app 端到端问答验收

### F1（已修复）构建入口目录变量异常

- 状态：Resolved
- 现象：build.py 主函数引用未定义的 LEARN_DIR，导致 NameError
- 修复：主函数改为动态组装 target_dirs，仅在 LEARN_DIR 已定义时追加
- 结果：构建流程可正常进入数据读取与向量化阶段

### F2（已完成）TDD 模块化重构基线

- 状态：Resolved
- 内容：
  - 抽离路由决策模块（graph_routes）并补充独立单测
  - 抽离反馈持久化模块（feedback.store）并补充独立单测
  - 抽离构建目录解析模块（build_utils）并补充独立单测
- 结果：核心组件可独立验证，降低入口文件耦合度，形成 TDD 可持续迭代基础

### M1（规划中）文档图片多模态增强

- 状态：Open
- 背景：当前 docs 入库内容包含 Markdown 图片引用（如 `![img](./_resources/xxx.png)`），但主链路尚未消费图片信息。
- 目标：在不破坏现有文本 RAG 的前提下，为图片内容补充可访问 URL 与后续多模态消费能力。
- 实施门禁：本项必须在“首次跑通整个项目”完成后再进入实现。

## 9. 多模态扩展计划（首次跑通后实施）

### 9.1 范围与目标

在 docs 文档中识别 Markdown 图片引用，并基于 `DocData URL` 构造图片可访问地址，形成“文本 + 图片元数据”增强上下文，为后续多模态问答打基础。

### 9.2 图片 URL 构造规则

输入前提：文档头部存在 `> DocData URL: .../dist/<path>/<name>_CN.md`。

规则：

1. 取 `DocData URL` 去掉文件名后的目录作为 `doc_base_dir`。
2. 若图片是相对路径（如 `./_resources/合集卡片预览.png`），拼接为：`doc_base_dir + /_resources/合集卡片预览.png`。
3. 若图片是绝对 URL（`http://` 或 `https://`），直接保留原值。
4. 对中文文件名进行 URL 编码后访问（存储时保留原文与编码后 URL 两份）。

示例（以 `collections/intro` 为例）：

- `DocData URL`：`https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/collections/intro/intro_CN.md`
- 图片引用：`![image.png](./_resources/创建合集.png)`
- 可访问 URL：`https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/collections/intro/_resources/创建合集.png`

- 图片引用：`![img.png](./_resources/合集卡片预览.png)`
- 可访问 URL：`https://resouces.modelscope.cn/document/docdata/2026-3-17_11-15-CN/dist/collections/intro/_resources/合集卡片预览.png`

### 9.3 分阶段实施

Phase A（元数据增强，不改推理链路）

1. 在构建阶段解析 Markdown 中的图片语法，提取：`alt`、`raw_path`、`resolved_url`、`source_doc`。
2. 将图片元数据写入切片 metadata（例如 `image_refs` 字段）。
3. 增加 URL 可达性探测（HEAD/GET），记录状态码与失败原因（不阻断主流程）。

Phase B（检索增强）

1. 检索命中文档时携带 `image_refs` 返回。
2. 在 rerank 前后保留图片关联信息，避免被丢失。

Phase C（生成增强）

1. 在回答中按段落关联展示图片链接（先文本链接，后续可扩展缩略图/预览）。
2. 明确回答策略：仅在图片与问题相关时引用，避免噪声。

### 9.4 验收标准

1. 对含图片的 docs 文档，`resolved_url` 生成正确率 >= 99%。
2. URL 探测失败不影响索引构建与主问答链路。
3. 对典型问题可在回答中返回对应图片链接，且来源可追溯到具体文档。
4. 新增单元测试覆盖：路径解析、中文路径编码、异常路径兜底。

### 9.5 风险与约束

1. 外链资源可能失效或限流，必须具备降级策略。
2. 中文路径在不同客户端编码行为不一致，需统一编码规范。
3. 本期不引入视觉模型推理（仅做图片链接与上下文增强），避免扩大范围。

## 10. 文档维护约定

- 每次改动必须同步更新 CHANGELOG.md
- 影响运行状态的变更必须同步更新本 SPEC 的“当前状态”和“问题清单”
- 问题状态使用：Open / In Progress / Resolved
- 协作场景下，助手改动与用户改动均应纳入同一轮变更记录，不遗漏本地人工修改
- 建议提交节奏：按功能或半天粒度至少完成一次“SPEC + CHANGELOG + git commit”闭环
- 提交信息应包含变更类型与范围（如 feat/fix/docs/chore + 模块名），便于后续追溯
