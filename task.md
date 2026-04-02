# ModelScope Agent Task（任务规划与进度）

更新时间：2026-04-02

## 1. 本轮任务

1. T-001 文档分层重构（Specscoding）
2. T-002 Skill 开发流程规范化（保留 TDD）
3. T-003 README 与 CHANGELOG 同步
4. T-004 评测相关用户改动纳入变更记录
5. T-005 修复 web_node LangChain 弃用告警与运行时异常
6. T-006 前端界面重构与交互优化（PC 优先）
7. T-007 修复 LLM 初始化阶段环境变量加载时序
8. T-008 增强 Router 解析失败可观测性
9. T-012 多模态图片直链解析与索引接入
10. T-013 文档教程化重写与提交闭环
11. T-016 LangSmith tracing 与 evaluate 接入及评测文档同步
12. T-018 优化 grade 节点性能，降低文档评分延迟
13. T-019 简单问题检索限流与数量观测日志

## 2. 进度看板

| 任务ID | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| T-001 | 重构 spec/plan/task 分层 | Done | 已新增 `spec.md`、`plan.md`、`task.md` 并完成职责分离 |
| T-002 | 调整 skill 开发流程 | Done | 已更新 autocoder/sync_doc，统一到 Specscoding + TDD 流程 |
| T-003 | 同步 README 与 CHANGELOG | Done | README 新增文档治理与开发流程约定，CHANGELOG 记录本轮变更 |
| T-004 | 对齐用户现有改动记录 | Done | 已纳入评测脚本与配置相关变更说明 |
| T-005 | 修复 web_node 弃用告警与字符串异常 | Done | 已迁移至 langchain-tavily，新增 7 个单元测试，32/32 测试通过 |
| T-006 | 前端界面重构与交互优化 | Done | `app.py` 完成 chat-first 单列布局、快捷提问胶囊、底部输入区与反馈区重排，重点优化滚动与空间占用 |
| T-007 | 修复环境变量加载时序 | Done | `src/llm/model_config.py` 增加 `load_dotenv()` 早期加载，避免模型初始化阶段读不到密钥 |
| T-008 | Router 兜底可观测性增强 | Done | `src/node/router.py` 在降级路径打印原始查询，便于线上排障 |
| T-012 | 多模态图片直链解析与索引接入 | Done | 已完成相对图链绝对化、构建侧兼容改写、图片 caption 并入检索、生成链路 `[[IMG:docid:idx]]` 注入与 `image_registry` 透传；caption prompt 已统一收敛到 `src/prompt/caption_prompt.py`，前端支持图片放大预览与 Ollama 快捷胶囊 |
| T-013 | 文档教程化重写与提交闭环 | Done | README 重写为学习入口（含学习路径、网页资源、AI coding 流程、commit 追踪）；同步 spec/plan/task/CHANGELOG 并完成提交 |
| T-016 | LangSmith tracing/evaluate 接入与文档同步 | Done | `run_eval.py` 新增 tracing/evaluate 参数；`src/eval/langsmith_sync.py` 增加 tracing 配置、样本去重上传与 evaluate API 调用；同步 README 与 `EVAL_LANGSMITH_GUIDE.md` 使用说明 |
| T-018 | 优化 `grade_node` 性能与延迟 | Done | 增加空文档短路逻辑（直接跳转重写或 web 分支），并针对 LLM 输入增加文档截断与 Top-N 限制，大幅降低 prompt token 量与请求耗时，新增相关单元测试 |
| T-019 | 简单问题检索限流与数量观测日志 | Done | 在 `src/node/retriever.py` 的 `retrieve_docs_node` 限制仅保留前 5 篇文档下游使用，并新增“命中数量/传入数量”日志；新增 `tests/unit/test_retriever_node.py` 覆盖该行为 |

## 3. 下一步任务池

1. T-009 为前端布局与交互补充可自动化回归检查（至少覆盖主布局与事件链）。
2. T-010 清理无关产物（本地图片、备份文件、历史反馈快照）并建立忽略策略。
3. T-011 评估 `run_eval_wrapped.py` 与 `run_eval.py` 的功能重叠，决定合并或保留。
4. T-012.1 在生成链路注入 `[[IMG:docid:idx]]` 占位符与 image_map 透传。（Done）
5. T-012.2 在 `app.py` 流式输出阶段实现占位符替换为 Markdown 图片直链。（Done）
6. T-012.3 统一管理 caption prompt（中文重写，适配技术文档操作截图场景）。（Done）
7. T-012.4 前端优化图片可读性（默认放大展示 + 点击 Lightbox 预览）并新增 Ollama 快捷胶囊。（Done）
9. T-014 将课程模块补齐为每模块 3-5 道场景题，并增加调试路径示例。
10. T-015 为课程产物补充轻量验收检查（导航点、动画、quiz 绑定完整性）。
11. T-017 为 `run_eval.py` 增加参数级单元测试（CLI 选项组合与错误分支）。
12. T-018.1 探索轻量规则预判 + LLM 兜底的二期优化（如果后续线上性能依然不及预期时回归）。
