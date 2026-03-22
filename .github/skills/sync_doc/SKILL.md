---
name: sync_doc
description: "Use when: 需要把助手改动和用户改动一起同步到 SPEC/CHANGELOG 并执行一次 git 提交。仅在较大功能变化、迭代优化、问题修复、阶段里程碑时触发。不要用于一行文案、注释增删、API 名称微调等小改动。关键词：同步文档、同步日志、同步SPEC、版本维护、里程碑提交。"
---

# sync_doc

## Decision Gate

先判断是否需要执行本 skill。

执行（任一满足）：

1. 新增/删除模块、接口、流程节点、测试集。
2. 行为变化会影响运行结果、验收结论或用户体验。
3. 解决了一个明确问题（bug、阻塞、稳定性问题）。
4. 完成一个阶段目标，准备做检查点提交或里程碑 tag。

跳过（全部满足时跳过）：

1. 仅注释或措辞微调。
2. 一行等价改写（不改变行为）。
3. 仅局部 API 名称替换且无行为变化。
4. 无需追溯记录的小修小补。

## Workflow

### 1) Collect

1. 执行 git status --short。
2. 执行 git diff --name-only（必要时区分 staged/unstaged）。
3. 将改动分组：功能、修复、测试、文档、配置。
4. 必须同时识别助手改动与用户改动。

### 2) Sync SPEC

至少更新：

1. 当前状态（完成/未完成）。
2. 问题状态（Open/In Progress/Resolved）。
3. 下一步或门禁条件（若变化）。

### 3) Sync CHANGELOG

在 Unreleased 下按需更新：

1. Added
2. Changed
3. Fixed
4. Planned（可选）

要求：每条都可映射到具体改动或行为变化。

### 4) Pre-commit Check

1. 排除敏感信息（如 .env、密钥、私有数据）。
2. 排除无关产物（缓存、临时目录、大文件）。
3. 有条件时执行最小验证（如 pytest -q 或关键命令）。

### 5) Commit

1. git add 目标文件。
2. git commit -m "<type>: <scope> <summary>"。

建议类型：feat、fix、docs、chore。

### 6) Optional Tag

阶段验收通过后可执行：

1. git tag -a vX.Y.Z -m "<milestone summary>"。

## Output Contract

执行后给出：

1. 是否触发本 skill（以及触发理由）。
2. 已同步的 SPEC/CHANGELOG 要点。
3. commit hash、提交信息、验证结果。

## Boundaries

1. 未经确认不提交敏感文件。
2. 未验证不写“已跑通”。
3. 若存在外部阻塞，提交说明必须显式标注。