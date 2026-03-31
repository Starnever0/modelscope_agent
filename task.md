# ModelScope Agent Task（任务规划与进度）

更新时间：2026-03-31

## 1. 本轮任务

1. T-001 文档分层重构（Specscoding）
2. T-002 Skill 开发流程规范化（保留 TDD）
3. T-003 README 与 CHANGELOG 同步
4. T-004 评测相关用户改动纳入变更记录
5. T-005 修复 web_node LangChain 弃用告警与运行时异常
6. T-006 前端界面重构与交互优化（PC 优先）
7. T-007 修复 LLM 初始化阶段环境变量加载时序
8. T-008 增强 Router 解析失败可观测性

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

## 3. 下一步任务池

1. T-009 为前端布局与交互补充可自动化回归检查（至少覆盖主布局与事件链）。
2. T-010 清理无关产物（本地图片、备份文件、历史反馈快照）并建立忽略策略。
3. T-011 评估 `run_eval_wrapped.py` 与 `run_eval.py` 的功能重叠，决定合并或保留。
