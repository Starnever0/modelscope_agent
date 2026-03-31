# ModelScope Agent Task（任务规划与进度）

更新时间：2026-03-31

## 1. 本轮任务

1. T-001 文档分层重构（Specscoding）
2. T-002 Skill 开发流程规范化（保留 TDD）
3. T-003 README 与 CHANGELOG 同步
4. T-004 评测相关用户改动纳入变更记录
5. T-005 修复 web_node LangChain 弃用告警与运行时异常

## 2. 进度看板

| 任务ID | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| T-001 | 重构 spec/plan/task 分层 | Done | 已新增 `spec.md`、`plan.md`、`task.md` 并完成职责分离 |
| T-002 | 调整 skill 开发流程 | Done | 已更新 autocoder/sync_doc，统一到 Specscoding + TDD 流程 |
| T-003 | 同步 README 与 CHANGELOG | Done | README 新增文档治理与开发流程约定，CHANGELOG 记录本轮变更 |
| T-004 | 对齐用户现有改动记录 | Done | 已纳入评测脚本与配置相关变更说明 |
| T-005 | 修复 web_node 弃用告警与字符串异常 | Done | 已迁移至 langchain-tavily，新增 7 个单元测试，32/32 测试通过 |

## 3. 下一步任务池

1. T-006 为评测脚本补充对应单元测试用例（TDD Red 起步）。
2. T-007 清理无关产物（本地证书、临时图、历史反馈文件）并建立忽略策略。
3. T-008 评估 `run_eval_wrapped.py` 与 `run_eval.py` 的功能重叠，决定合并或保留。
