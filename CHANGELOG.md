# Changelog

本项目采用持续更新日志，记录功能变更、问题修复与运行状态变化。

## [Unreleased]

### Added

- 新增 SPEC 文档：SPEC.md
- 明确首轮目标为“跑通全链路（抓取数据 -> 构建索引 -> 启动服务 -> 完成一次 docs 问答）”
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

### Planned

- 多模态增强实施门禁：必须在首次“全链路跑通”完成后启动
- Phase A/B/C 分阶段推进：图片元数据增强 -> 检索保留图片关联 -> 生成阶段按相关性引用图片

### Changed

- 运行环境基线统一为 uv
- 验证命令统一为 uv run python <script>
- 测试命令口径统一为 `uv run python -m pytest -q`，确保使用项目 `.venv` 的解释器与依赖
- 修复 build.py 目录组装逻辑，避免 LEARN_DIR 未定义导致 NameError
- app.py 不再内嵌反馈 JSON 落盘逻辑，改为调用独立反馈存储模块
- src/graph.py 不再内嵌路由判定实现，改为调用独立路由模块
- 文档治理范围扩展为“代码 + 文档 + 用户本地改动”的统一变更日志管理
- src/embedding/embedding.py 改为从模型配置中心获取 embedding 实例
- src/node/rerank.py 改为从模型配置中心调用 rerank，移除重复模型名与 API Key 处理
- src/llm/provider.py 改为兼容层，底层统一走模型配置中心
- README 新增“模型统一配置”说明，明确一处改模型名
- src/llm/model_config.py 新增文本/多模态模型分层配置，并支持 `RAG_EMBEDDING_MODEL` 与 `RAG_RERANK_MODEL` 覆盖
- src/llm/model_config.py 调整为“文本向量化固定走 text-embedding，多模态模型仅用于图文向量化”
- src/llm/model_config.py 将 `normal_chat` 切换为当前账号可用模型 `qwen-turbo`，`stream_chat` 保持 `qwen3-max-2026-01-23`
- src/llm/provider.py 与核心节点改为场景化获取 LLM，以输出可追踪的模型调用日志
- app.py 的 Gradio 启动默认绑定地址由 `0.0.0.0` 调整为 `127.0.0.1`，并支持 `GRADIO_SERVER_NAME/GRADIO_SERVER_PORT/GRADIO_INBROWSER` 环境变量覆盖
- app.py 移除 Chatbot 已弃用参数 `bubble_full_width`，消除启动告警
- `pyproject.toml` 新增 `langsmith` 依赖，用于评测数据集与结果上传
- EVAL 评测说明文档已切换为中文版本，统一测试集构建与输入指引口径
- 开发流程新增“文档撰写优先中文”规范，并明确开发前必读文档清单（SPEC/README/评测任务附加 EVAL 指引）

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

### Fixed

- 将 `pytest` 加入 uv 开发依赖组，修复 uv 测试链路误命中全局 pytest 的问题
- 修复 `normal_chat=qwen3.5-flash` 在当前账号下触发 `InvalidParameter(url error)` 导致主链路中断的问题
- 解决 Embedding 欠费导致的索引构建阻塞，已恢复 `build.py` 构建产物
- 修复 Gradio 启动后输出地址不可直接访问的问题（0.0.0.0 -> 127.0.0.1）

### Known Issues

- 当前无已知阻塞问题。
