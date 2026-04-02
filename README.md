# ModelScope Agent

一个面向 ModelScope 场景的 RAG Agent 项目。

它既是可运行的社区答疑系统，也是可复用的 RAG 教程工程：你可以从抓取、索引、检索、生成、评测到反馈闭环，完整学习一套可落地的 AI 应用开发路径。

## 这个项目能做什么

1. 社区问答：基于 LangGraph 路由，区分闲聊与文档问答。
2. 混合检索：FAISS 向量检索 + BM25 关键词检索，支持并行召回。
3. 质量增强：查询重写、文档评分、重排序与兜底搜索。
4. 多模态扩展：文档图片链接、caption 注入与占位符渲染。
5. 评测闭环：检索指标、时延指标、LLM-as-judge + LangSmith 上传。

## 为什么它适合做 RAG 教程

1. 全链路完整：不是孤立 demo，而是从数据到线上问答的完整工程。
2. 文档分层清晰：目标、计划、任务、变更日志都有明确边界。
3. 可追踪演进：可通过 commit 历史与 CHANGELOG 回放每次设计决策。
4. 命令统一：统一 `uv run ...`，降低环境偏差与复现实验成本。

## 学习路径（建议按顺序）

### 路径 1：先跑起来（30-60 分钟）

1. 安装依赖并配置 `.env`。
2. 启动应用并完成 1 次 docs 问答。
3. 观察日志中的模型路由、检索与生成输出。

### 路径 2：理解数据与索引（1-2 小时）

1. 阅读 `crawl/README.md` 与 `crawl/crawl.py`，理解抓取策略。
2. 执行抓取并查看 `data/raw/` 与 `data/crawl_state.json`。
3. 执行 `build.py`，理解切分、embedding 与向量索引构建流程。

### 路径 3：理解 RAG 核心链路（2-4 小时）

1. 从 `src/graph.py` 看整体状态机与分支。
2. 重点阅读 `src/node/router.py`、`src/node/retriever.py`、`src/node/parallel_retrieve.py`、`src/node/generate.py`。
3. 对照 `src/graph_routes.py` 理解条件边决策。

### 路径 4：学会评测（1-2 小时）

1. 阅读 `EVAL_LANGSMITH_GUIDE.md`。
2. 跑通 `scripts/run_eval.py`，理解检索/时延/生成质量指标。
3. 尝试构建自己的评测集并上传 LangSmith。

### 路径 5：按 AI Coding 流程迭代（持续）

1. 在 `spec.md` 明确目标和约束。
2. 在 `plan.md` 制定阶段策略与里程碑。
3. 在 `task.md` 拆分任务并更新状态。
4. 代码与文档同步更新后，回写 `CHANGELOG.md`。
5. 通过 commit 记录形成可追溯迭代链路。

## 文档治理（Specscoding）

请按下面顺序阅读与维护：

1. `spec.md`：目标、范围、约束、验收。
2. `plan.md`：阶段计划、策略、里程碑、风险。
3. `task.md`：任务拆解、状态、下一步。
4. `CHANGELOG.md`：变更记录与验证证据。

## 快速开始

### 1) 获取代码

```bash
git clone https://www.modelscope.cn/studios/kirito1223/modelscope_agent.git
cd modelscope_agent
```

### 2) 安装与环境

```bash
# 安装 uv（任选其一）
pip install uv
# 或
pipx install uv

# 安装依赖
uv pip install -r requirements.txt
```

### 3) 配置 `.env`

```bash
# 必填：阿里云 DashScope API Key
DASHSCOPE_API_KEY=your_dashscope_api_key

# 可选：联网搜索
TAVILY_API_KEY=your_tavily_api_key
```

### 4) 运行应用

```bash
uv run python app.py
```

### 5) 常用命令

```bash
# 单次抓取
uv run python crawl.py

# 循环抓取（每 3 小时）
uv run python crawl.py --loop --interval-minutes 180

# 重建向量索引
uv run python build.py

# 运行评测
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10

# 启用 LangSmith tracing（仅追踪）
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10 --langsmith-tracing --langsmith-project modelscope-rag

# 上传本地评测摘要到 LangSmith
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --upload-langsmith --dataset-name modelscope_rag_eval

# 运行 LangSmith evaluate 实验（会在平台创建实验）
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --dataset-name modelscope_rag_eval --langsmith-evaluate --langsmith-experiment-prefix modelscope-rag-eval
```

## 项目结构（学习视角）

```text
app.py                         # Gradio 入口与流式响应
build.py                       # Markdown -> chunk -> embedding -> FAISS
crawl/                         # 数据抓取与链接治理
src/graph.py                   # LangGraph 工作流编排
src/graph_routes.py            # 路由条件函数
src/node/                      # 核心节点（router/retrieve/rewrite/rerank/generate/...）
src/eval/                      # 评测模块
src/llm/model_config.py        # 模型统一配置
data/eval/datasets/            # 评测数据
scripts/                       # 数据与评测脚本
tests/unit/                    # 单元测试
```

## 网页学习资源

1. ModelScope 文档中心：https://www.modelscope.cn/docs/overview
2. ModelScope 研习社：https://modelscope.cn/learn
3. ModelScope GitHub 组织：https://github.com/modelscope
4. 本项目评测指南：`EVAL_LANGSMITH_GUIDE.md`
5. 本项目课程产物：`course-modelscope-agent/index.html`

## 如何追踪演进与决策

1. 看变更日志：`CHANGELOG.md`
2. 看任务状态：`task.md`
3. 看提交历史：

```bash
git log --oneline --decorate --graph -n 30
```

4. 查看某个模块历史：

```bash
git log --oneline -- src/node/retriever.py
```

## 模型配置说明

模型名称统一在 `src/llm/model_config.py` 维护。常用场景包括：

1. `intent_router`：路由决策。
2. `query_rewrite` / `query_decompose`：重写与分解。
3. `doc_grade` / `rerank`：检索质量增强。
4. `answer_generate` / `chat_generate`：最终回答。
5. `embedding_text`：向量化。

## 致谢与参考

本项目参考并继承了 ModelScope Studio 社区实践，原始工程地址如下：

https://www.modelscope.cn/studios/kirito1223/modelscope_agent.git

感谢社区贡献者持续公开迭代思路、提交记录与实践经验，为 RAG 工程学习提供了高质量样本。

## 许可证

Apache License 2.0