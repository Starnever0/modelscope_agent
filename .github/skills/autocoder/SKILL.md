---
name: autocoder
description: "Use when: 需要按项目规范进行完整开发流程。开发前先读 spec/plan/task，开发中保持 TDD，开发后判断是否触发 sync_doc 并完成文档与提交闭环。关键词：Specscoding、TDD、文档分层、开发门禁、sync_doc。"
---

# autocoder

## Purpose

统一开发流程，确保每次开发都遵循 Specscoding 文档分层与 TDD 研发范式。

## Mandatory Workflow

### 1) Pre-Dev: Read Required Docs

任何代码改动前，必须先读取：

1. `spec.md`（强制，目标与约束）
2. `plan.md`（强制，整体计划）
3. `task.md`（强制，任务与进度）
4. `README.md`（强制，运行与开发约定）
5. `EVAL_LANGSMITH_GUIDE.md`（评测任务时强制）

开发前提取并确认：

1. 本轮目标与硬约束。
2. 当前任务状态与优先级。
3. 运行与验证命令口径（统一 `uv run ...`）。

若 `spec.md` 与用户最新要求冲突：

1. 先按用户明确要求执行。
2. 开发后同步回写文档（通过 sync_doc 门禁判断）。

### 2) Dev: Implement With TDD

开发过程必须执行 TDD：

1. Red：先写失败测试，先定义行为。
2. Green：实现最小改动使测试通过。
3. Refactor：保持测试通过前提下重构。

同时遵守：

1. 变更范围最小化，避免无关重构。
2. 优先保持公共接口稳定。
3. 能验证就验证，不伪造结果。
4. 对外部阻塞显式标注。

### 3) Post-Dev: Update Task Progress

开发完成后，先更新 `task.md`：

1. 将已完成事项改为 Done。
2. 将当前执行项标记为 In Progress 或 Done。
3. 记录下一步任务池。

### 4) Decide Doc Sync Gate

满足任一条件需触发 `sync_doc`：

1. 新增/删除模块、接口、流程节点、测试集。
2. 行为变化影响运行结果、验收结论或用户体验。
3. 修复明确问题（bug、阻塞、稳定性）。
4. 达到阶段性里程碑，需要可追溯提交。

若仅为注释或等价微调，且无行为变化，可跳过。

## Output Contract

每次使用本 skill 后，输出至少包含：

1. 是否已读取 `spec.md` / `plan.md` / `task.md`。
2. 本轮遵循的关键约束。
3. TDD 执行状态（Red/Green/Refactor）。
4. 是否触发 `sync_doc` 及理由。

## Boundaries

1. 不得跳过“先读 spec/plan/task”。
2. 不得跳过 TDD 直接实现。
3. 未验证不写“已跑通”。
4. 未经确认不提交敏感文件。
