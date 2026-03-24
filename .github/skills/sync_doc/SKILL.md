---
name: sync_doc
description: "Use when: 需要把助手改动和用户改动同步到 spec/plan/task/CHANGELOG，并完成一次可追溯 git 提交。用于功能迭代、问题修复、里程碑检查点。关键词：Specscoding、文档同步、任务进度、变更日志、提交闭环。"
---

# sync_doc

## Decision Gate

先判断是否执行本 skill。

执行（任一满足）：

1. 新增/删除模块、接口、流程节点、测试集。
2. 行为变化影响运行结果、验收结论或用户体验。
3. 解决明确问题（bug、阻塞、稳定性）。
4. 达到阶段里程碑，需要检查点提交。

跳过（全部满足时）：

1. 仅注释或措辞微调。
2. 一行等价改写且无行为变化。
3. 局部重命名且无行为变化。
4. 无需追溯记录的小修。

## Workflow

### 1) Collect Changes

1. 执行 `git status --short`。
2. 执行 `git diff --name-only`。
3. 分组改动：功能、修复、测试、文档、配置、用户本地改动。
4. 明确哪些文件不应提交（证书、缓存、临时产物、私密数据）。

### 2) Sync Specscoding Docs

1. `spec.md`：仅在目标/约束变化时更新。
2. `plan.md`：同步阶段策略与里程碑变化。
3. `task.md`：同步任务状态（Todo/In Progress/Done）与下一步。
4. `CHANGELOG.md`：记录 Added/Changed/Fixed/Planned，每条可映射到文件或行为。

### 3) Sync Related Guides

按改动模块同步相关文档：

1. 根 README 或模块 README。
2. 领域指南（如评测改动对应 `EVAL_LANGSMITH_GUIDE.md`）。
3. 新增脚本的使用说明。

若无需更新，需给出明确理由。

### 4) Pre-commit Check

1. 保留 TDD 证据：至少给出一次可执行验证（测试或关键命令）。
2. 排除敏感信息与无关产物。
3. 检查提交范围与变更说明一致。

### 5) Commit

1. `git add` 目标文件。
2. `git commit -m "<type>: <scope> <summary>"`。
3. 返回 commit hash 与提交说明。

## Output Contract

执行后给出：

1. 触发理由。
2. 已同步文档清单（spec/plan/task/changelog/readme/相关指南）。
3. 验证结果（包含 TDD 相关验证信息）。
4. commit hash 与提交信息。

## Boundaries

1. 未经确认不提交敏感文件。
2. 未验证不写“已跑通”。
3. 只同步有依据的变更，不编造记录。
