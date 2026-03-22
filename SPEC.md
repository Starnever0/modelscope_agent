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

## 9. 文档维护约定

- 每次改动必须同步更新 CHANGELOG.md
- 影响运行状态的变更必须同步更新本 SPEC 的“当前状态”和“问题清单”
- 问题状态使用：Open / In Progress / Resolved
