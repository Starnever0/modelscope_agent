---
name: spec-changelog-commit-loop
description: "Use when: 需要定期将助手改动和用户改动一起回写到 SPEC/CHANGELOG 并执行 git 提交；关键词：更新日志、SPEC同步、版本维护、定期commit、里程碑提交"
---

# Spec + Changelog + Commit Loop

## 目标

将仓库中的实际改动（包括助手改动与用户改动）周期性收敛为可追溯版本：

1. 盘点变更
2. 回写 SPEC 与 CHANGELOG
3. 执行一次可回滚的 git commit

## 适用场景

1. 一个功能阶段完成后
2. 半天或一天结束时
3. 修复若干零散问题后
4. 准备发版 tag 前

## 输入

1. 当前工作区改动（git status）
2. 运行验证结果（测试、构建、关键命令）
3. 已知风险与阻塞

## 标准步骤

### Step 1: 盘点改动

1. 执行 git status --short
2. 执行 git diff --name-only（必要时分 staged/unstaged）
3. 将改动分组：功能、修复、文档、测试、配置

### Step 2: 回写 SPEC

至少更新以下内容：

1. 当前状态（已完成/未完成）
2. 问题清单（Open/In Progress/Resolved）
3. 验收标准或下一步计划（若有变化）

要求：

1. 记录事实，不写空泛描述
2. 明确阻塞是否来自外部依赖
3. 与当次改动对应，不跨版本混写

### Step 3: 回写 CHANGELOG

在 Unreleased 下更新：

1. Added：新增能力、模块、测试
2. Changed：行为变化、重构、流程变化
3. Fixed：缺陷修复
4. Planned（可选）：明确门禁与后续阶段计划

要求：

1. 同时覆盖助手改动与用户改动
2. 每条描述可映射到具体文件或行为

### Step 4: 提交前检查

1. 确认不提交敏感信息（.env、密钥、私密数据）
2. 确认不误提交流程产物（临时目录、缓存、无关大文件）
3. 必要时先运行最小验证（如 pytest -q 或关键脚本）

### Step 5: 提交

1. git add 目标文件
2. git commit -m "<type>: <scope> <summary>"

推荐提交信息：

1. feat: <module> <summary>
2. fix: <module> <summary>
3. docs: spec/changelog sync for <scope>
4. chore: checkpoint commit for <scope>

### Step 6: 里程碑（可选）

满足阶段验收后：

1. git tag -a vX.Y.Z -m "<milestone summary>"

## 产出模板

### 变更摘要

1. 本轮完成：...
2. 本轮阻塞：...
3. 下一步：...

### 提交摘要

1. commit: <hash>
2. scope: <files/modules>
3. verification: <passed/failed + command>

## 执行边界

1. 不自动提交用户未同意纳入版本的敏感文件
2. 不在未核实情况下写“已跑通”
3. 阻塞未解时，提交信息应显式标注当前限制
