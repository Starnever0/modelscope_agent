# Changelog

本项目采用持续更新日志，记录功能变更、问题修复与运行状态变化。

## [Unreleased]
### Changed

- 文档教程化重构：README 重写为项目学习入口
  - 新增“RAG 教程学习路径”（从跑通链路到评测与迭代）
  - 新增网页学习资源索引与 AI coding 开发流程说明
  - 新增 commit 追踪使用方式（`git log` 与按文件追踪）
  - 新增“致谢与参考”章节并引用 ModelScope Studio 原项目链接

- Specscoding 文档同步升级
  - `spec.md` 增加“教程化目标、学习资产范围、可追溯约束、教程验收”
  - `plan.md` 增加 Phase C.1（教程化与学习资产）与里程碑/风险同步
  - `task.md` 新增 T-013（文档教程化重写与提交闭环）并标记完成

### Added

- 新增课程学习产物目录：`course-modelscope-agent/`
  - 包含 `index.html`、模块化课程页面与静态资源（可直接浏览器打开）

### Added

- 新增图片相对链接绝对化能力（DocData URL 优先，Source URL 回退）
  - `crawl/crawl.py` 新增 `absolutize_markdown_image_links()` 与 `resolve_image_target_url()`
  - `fetch_docdata_markdown()` 产出 Markdown 前会将 `![alt](./_resources/...)` 改写为可访问绝对 URL
  - 影响：后续多模态链路可直接使用图片直链，无需本地下载

- 新增构建侧图片链接兼容改写
  - `build.py` 新增 `absolutize_markdown_image_links()`，在切分前基于 `DocData URL/Source URL` 进行改写
  - 影响：历史存量文档在不重跑全量抓取时也可获得图片绝对链接

- 新增单元测试
  - `tests/unit/test_crawl_image_links.py` 覆盖 DocData 优先、Source 回退与不改写绝对链接场景
  - `tests/unit/test_build_metadata.py` 补充 `DocData URL` 解析与构建侧图片改写测试
  - `tests/unit/test_generate_node.py` 覆盖生成链路占位符注入与 `image_registry` 透传

- 新增生成链路多模态占位符注入与映射透传
  - `src/node/generate.py` 新增图片映射规范化与上下文组装逻辑：为命中文档生成 `[[IMG:docid:idx]]` 占位符并写入 `context`
  - `src/node/generate.py` 返回新增字段 `image_registry`（placeholder -> image_url），供前端流式替换使用
  - `src/state/state.py` 扩展 `image_registry` 状态字段
  - `src/prompt/generator_prompt.py` 增加占位符保真约束，要求保留 `[[IMG:docid:idx]]`

- 新增前端流式占位符替换能力（`[[IMG:docid:idx]]` -> Markdown 图片直链）
  - `src/placeholder_render.py` 新增占位符渲染与图状态读取工具函数
  - `app.py` 在 `bot_response` 流式循环中接入 `image_registry` 读取与实时重渲染，支持映射延迟可用时回填替换
  - 流式结束后增加一次最终刷新，确保尾段占位符完成替换
  - 异常分支同样走占位符渲染，避免错误提示前残留未替换占位符

- 新增单元测试
  - `tests/unit/test_placeholder_render.py` 覆盖占位符替换、未知占位符保留、图状态读取成功与异常兜底场景

- 新增图片 caption 并入检索能力（构建阶段）
  - `build.py` 在切分前解析图片并注入检索文本块：`placeholder + caption`
  - `build.py` 新增 `docid` 生成、`image_map`/`has_image`/`image_count` metadata 写入
  - `src/multimodal/caption.py` 新增多模态图片描述生成工具，失败自动回退到 alt 文本描述
  - `src/llm/model_config.py` 新增 `caption_multimodal` 模型配置项与 `RAG_MULTIMODAL_CAPTION_MODEL` 覆盖能力
  - `src/llm/provider.py` 新增 `get_multimodal_llm_for_scene()` 供图片描述场景调用
  - 新增 `BUILD_ENABLE_IMAGE_CAPTION` 开关与 caption 缓存，降低构建耗时与外部依赖波动影响

- 新增统一 caption prompt 管理（中文重写）
  - 新增 `src/prompt/caption_prompt.py`，集中维护图片 caption 提示词模板
  - `src/multimodal/caption.py` 改为引用统一 prompt 文件，避免业务逻辑中内联提示词
  - 提示词重写为“信息抽取优先”的技术文档场景模板，重点覆盖按钮名、字段名、参数名、流程步骤提取

- 新增前端图片可读性与交互优化
  - `app.py` 将快捷胶囊首项调整为“如何使用Ollama加载ModelScope模型？”
  - `app.py` 增强聊天图片默认展示尺寸，提升图文答疑可读性
  - `app.py` 新增图片 Lightbox 预览（点击放大、遮罩点击关闭、ESC 关闭）

### Fixed

- 修复 `src/llm/model_config.py` 中环境变量加载时序问题
  - 问题根因：部分运行路径下模型初始化早于 `.env` 注入，导致 `DASHSCOPE_API_KEY` 等密钥读取失败
  - 解决方案：在模型配置模块顶部显式执行 `load_dotenv()`，确保任何 LLM/Embedding/Rerank 初始化前完成环境加载
  - 影响：降低应用启动与链路初始化阶段的环境变量缺失错误

- 增强 `src/node/router.py` 的兜底可观测性
  - 在 Router 解析失败降级到 `docs` 路径时，新增原始查询日志输出
  - 影响：便于定位路由失败场景与复盘输入上下文

- 修复 `src/node/web.py` 中 TavilySearchResults 的弃用告警与字符串处理异常
  - 问题根因：LangChain 0.3.25+ 弃用 `langchain_community.tools.TavilySearchResults`，新版 `langchain-tavily` 返回 JSON 字符串而非字典列表，导致 `'str' object has no attribute 'get'` 异常
  - 解决方案：
    1. 迁移至 `langchain-tavily` 包的 `TavilySearch` 类（新官方实现）
    2. 新增 `langchain-tavily` 依赖到 pyproject.toml
    3. 增强 `web_node()` 以处理 JSON 字符串、字典、列表等多种返回格式
    4. 新增 7 个单元测试（tests/unit/test_web_node.py）覆盖各种格式与边界条件
  - 影响：消除 LangChainDeprecationWarning，修复 web 搜索节点的运行时异常
### Changed

- 重构 `app.py` 前端界面为 PC 优先的 chat-first 布局
  - 调整为单列会话主区域，突出聊天内容显示占比
  - 将快捷提问、输入框与反馈区收敛到底部 dock，降低视线切换成本
  - 细化滚动容器控制，缓解多重滚动条与会话区域压缩问题
  - 更新欢迎语与快捷提问交互链路，统一提交/发送/快捷按钮行为

- 文档体系重构为 Specscoding 分层：`spec.md`（目标约束）、`plan.md`（整体计划）、`task.md`（任务进度）、`CHANGELOG.md`（变更记录）
- 规范文档入口统一为 `spec.md`（替代历史 `SPEC.md` 命名）
- `README.md` 同步文档分层规范，并明确保留 TDD（Red/Green/Refactor）与 `uv run` 命令口径
- skill 流程规范升级：`autocoder` 与 `sync_doc` 增加 Specscoding 分层门禁、任务跟踪与提交闭环要求
- `scripts/prepare_eval_dataset.py` 增强 CSV 兼容能力：新增乱码修复与“问题/答案合并列”解析
- `src/eval/dataset_io.py` 补充中文字段语义说明，便于评测数据结构对齐
- `src/llm/model_config.py` 新增 `eval_candidate_generate` 模型配置项

### Added

- 新增文档：`spec.md`
- 新增文档：`plan.md`
- 新增文档：`task.md`
- 新增脚本：`scripts/diagnose_docid.py`（用于 docid 一致性诊断）
- 新增脚本：`scripts/run_eval_wrapped.py`（环境变量预加载的评测入口包装）
- 新增示例配置：`.env.example`

### Fixed

- 修复真实用户风格生成脚本的提示词解码约束问题（JSON 花括号转义），避免 ChatPromptTemplate 误解析导致 fallback
- 修复检索评测脚本的 docid 匹配逻辑：改用基于 source_urls 的匹配规避 hash 不一致问题
  - 问题根因：`build_docid_from_document()` 使用不同 chunk_index 计算 hash，导致文档虽检索正确但 docid 不匹配
  - 解决方案：优先使用数据集中已有的 source_urls 进行匹配（100% 精确）
  - 影响：Hit@k, Recall@k, MRR@k 指标从 2.5% 大幅提升至 95% 以上
- 优化 run_retrieval_eval.py 代码结构，支持 URL 优先、docid 回退的双模式匹配

### Added

- 新增“真实用户风格”评测集生成脚本：`scripts/generate_eval_realistic_qa.py`（生成 `query + reference_answer + expected_docids`）
- 新增专用检索评测脚本：`scripts/run_retrieval_eval.py`（快速计算 Hit@k、Recall@k、MRR@k，跳过生成阶段）
- 新增 80 个官方评测数据集：`data/eval/datasets/auto_questions_docid_80.jsonl`（LLM 生成、结构化解码、自动标注 docid）
- 新增评测报告生成能力（仅检索指标、完整评测）
- 新增 SPEC 文档：SPEC.md
- 明确首轮目标为"跑通全链路（抓取数据 -> 构建索引 -> 启动服务 -> 完成一次 docs 问答）"
- 建立问题挖掘与迭代更新机制（SPEC + CHANGELOG 联动）
- 新增 pytest 配置与单元测试集（tests/unit）
- 新增模块：src/graph_routes.py（路由决策）
- 新增模块：src/feedback/store.py（反馈持久化）
- 新增模块：src/build_utils.py（构建目录解析）
- 新增多模态扩展计划（写入 SPEC）：支持基于 DocData URL 构造 Markdown 图片可访问链接
- 新增协作治理约定：除助手改动外，用户改动也纳入定期 SPEC/CHANGELOG 回写与版本提交
- 新增统一模型配置中心：src/llm/model_config.py（集中管理 LLM/Embedding/Rerank 模型名与调用）
- 新增运行时模型观测日志：按调用场景打印真实模型名（intent/rewrite/decompose/grade/generate/embedding/rerank）
- 新增 LangSmith 评测模块：`src/eval/`（dataset/docid/retrieval/latency/judge/langsmith_sync）
- 新增评测执行脚本：`scripts/run_eval.py`
- 新增评测测试集模板：`data/eval/datasets/sample_rag_eval.jsonl`
- 新增评测指引文档：`EVAL_LANGSMITH_GUIDE.md`
- 新增评测单元测试：`tests/unit/eval/*.py`
- 新增数据集转换脚本：`scripts/prepare_eval_dataset.py`（支持标准问答/反馈数据 CSV 转 JSONL）
- 新增候选集生成脚本：`scripts/generate_eval_candidates.py`（按文档主题分批调用 LLM 生成 simple/medium/hard 问题并标记人工审核）
- 新增评测指标模块：`src/eval/answer_eval.py`（文本相似度）、`src/eval/feedback_eval.py`（用户评分与反馈覆盖率）

### Planned

- 多模态增强实施门禁：必须在首次"全链路跑通"完成后启动
- Phase A/B/C 分阶段推进：图片元数据增强 -> 检索保留图片关联 -> 生成阶段按相关性引用图片

### Changed

- `EVAL_LANGSMITH_GUIDE.md` 补充真实用户风格评测集构建说明与 100 条生成命令示例
- 文档治理规则扩展：除 SPEC/CHANGELOG 外，功能相关模块 README（含评测文档）需随迭代同步更新
- 运行环境基线统一为 uv
- 验证命令统一为 uv run python <script>
- 测试命令口径统一为 `uv run python -m pytest -q`，确保使用项目 `.venv` 的解释器与依赖
- 修复 build.py 目录组装逻辑，避免 LEARN_DIR 未定义导致 NameError
- app.py 不再内嵌反馈 JSON 落盘逻辑，改为调用独立反馈存储模块
- src/graph.py 不再内嵌路由判定实现，改为调用独立路由模块
- 文档治理范围扩展为"代码 + 文档 + 用户本地改动"的统一变更日志管理
- src/embedding/embedding.py 改为从模型配置中心获取 embedding 实例
- src/node/rerank.py 改为从模型配置中心调用 rerank，移除重复模型名与 API Key 处理
- src/llm/provider.py 改为兼容层，底层统一走模型配置中心
- README 新增"模型统一配置"说明，明确一处改模型名
- src/llm/model_config.py 新增文本/多模态模型分层配置，并支持 `RAG_EMBEDDING_MODEL` 与 `RAG_RERANK_MODEL` 覆盖
- src/llm/model_config.py 调整为"文本向量化固定走 text-embedding，多模态模型仅用于图文向量化"
- src/llm/model_config.py 将 `normal_chat` 切换为当前账号可用模型 `qwen-turbo`，`stream_chat` 保持 `qwen3-max-2026-01-23`
- src/llm/provider.py 与核心节点改为场景化获取 LLM，以输出可追踪的模型调用日志
- app.py 的 Gradio 启动默认绑定地址由 `0.0.0.0` 调整为 `127.0.0.1`，并支持 `GRADIO_SERVER_NAME/GRADIO_SERVER_PORT/GRADIO_INBROWSER` 环境变量覆盖
- app.py 移除 Chatbot 已弃用参数 `bubble_full_width`，消除启动告警
- `pyproject.toml` 新增 `langsmith` 依赖，用于评测数据集与结果上传
- EVAL 评测说明文档已切换为中文版本，统一测试集构建与输入指引口径
- 开发流程新增"文档撰写优先中文"规范，并明确开发前必读文档清单（SPEC/README/评测任务附加 EVAL 指引）
- 评测流程放宽为"docid 可选"：无 docid 数据集可跳过召回指标，继续执行速度/文本相似度/LLM-as-judge
- 支持反馈数据集直接复用历史机器人回答（不强制重新生成）
- LangSmith 上传样本字段扩展：支持 bot_answer、user_rating、user_feedback、dataset_type
- `scripts/generate_eval_candidates.py` 调整为"仅生成问题，不生成参考答案"，并支持 `question-count/docs-per-prompt/max-questions-per-call` 控制规模与调用次数
- `scripts/generate_eval_candidates.py` 新增 Pydantic 结构化解码与 JSON 清洗解析，降低 LLM 输出格式漂移导致的降级概率
- 自动样本 metadata 新增 `generation_source`（`llm`/`fallback`），支持用微任务快速定位是否触发降级

### Verified

- uv --version 可用
- uv run python --version 可用
- uv run python app.py 可启动 Gradio 服务
- uv run python -m pytest -q 通过（9 passed）
- data/faiss_db 可加载，向量库条目数为 4408
- 图流程 docs 问答端到端验证通过（可返回有效回答）
- 在不重建向量库条件下完成简单测试：单次图流程问答成功，并额外完成 rerank API 调用（status=200）
- 运行日志可见真实模型名打印：`embedding_text=text-embedding-v4`、`rerank=qwen3-rerank`、`intent_router/query_rewrite/query_decompose/doc_grade=qwen-turbo`、`answer_generate/chat_generate=qwen3-max-2026-01-23`
- `uv run python app.py` 启动后可通过 `http://127.0.0.1:7860` 打开页面
- `uv run python -m pytest tests/unit/eval -q` 通过（10 passed）
- `uv run python -m pytest -q` 全量通过（19 passed）
- `uv run python -m pytest tests/unit/eval -q` 再次通过（16 passed）
- `uv run python -m pytest -q` 全量再次通过（25 passed）
- 检索评测指标验证通过：Hit@10=95%、Recall@10=88.125%、MRR@10=0.853542（80 样本均使用 URL 匹配）

### Fixed (Previous)

- 将 `pytest` 加入 uv 开发依赖组，修复 uv 测试链路误命中全局 pytest 的问题
- 修复 `normal_chat=qwen3.5-flash` 在当前账号下触发 `InvalidParameter(url error)` 导致主链路中断的问题
- 解决 Embedding 欠费导致的索引构建阻塞，已恢复 `build.py` 构建产物
- 修复 Gradio 启动后输出地址不可直接访问的问题（0.0.0.0 -> 127.0.0.1）
- 修复自动问题生成中"弱问句高重复"与"LLM 输出不规范导致频繁 fallback"问题

### Known Issues

- 当前无已知阻塞问题。
