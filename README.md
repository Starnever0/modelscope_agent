# ModelScope Agent

基于 LangGraph 的智能问答代理系统，集成了检索增强生成（RAG）、文档评分、查询重写等多种功能。

## 功能特点

- 🤖 智能路由：自动判断问题类型，选择最优处理路径
- 📚 文档检索：支持向量数据库检索和 Web 搜索
- 🔄 查询重写：优化搜索查询以提高检索效果
- ⚡ 并行处理：支持多路径并行检索
- 📊 文档评分：智能评估文档相关性
- 🎯 重排序：对检索结果进行重新排序

## 项目结构

```
modelscope_agent/
├── app.py              # 主应用入口
├── build.py            # 构建脚本
├── requirements.txt    # 依赖包列表
├── data/              # 数据文件
│   └── faiss_db/      # FAISS 向量数据库
├── src/
│   ├── graph.py       # LangGraph 工作流定义
│   ├── embedding/     # 向量嵌入模块
│   ├── llm/          # 大语言模型接口
│   ├── node/         # 图节点实现
│   ├── prompt/       # 提示词模板
│   └── state/        # 状态管理
└── feedback_data/    # 用户反馈数据
```

## 快速开始

### 克隆项目

```bash
git clone https://www.modelscope.cn/studios/kirito1223/modelscope_agent.git
cd modelscope_agent
```

### 使用 uv 管理环境（推荐）

```bash
# 安装 uv（任选其一）
pip install uv
# 或
pipx install uv

# 创建并激活虚拟环境
uv venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
```

### 使用 pip（兼容方式）

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python app.py
```

## 数据抓取与持续更新

项目提供 `crawl.py`，用于抓取并持续更新以下来源并保存为 Markdown：

- 文档中心：https://www.modelscope.cn/docs/overview
- 研习社：https://modelscope.cn/learn
- GitHub 组织技术文档：https://github.com/modelscope
- 模型库：https://modelscope.cn/models
- 数据集：https://modelscope.cn/datasets
- 创空间应用：https://modelscope.cn/studios
- MCP：https://www.modelscope.cn/mcp
- AIGC 生图和训练：https://www.modelscope.cn/aigc

### 单次抓取

```bash
uv run python crawl.py
```

对于 `docs` 来源，爬虫会优先尝试官方 docdata Markdown 源（例如 `.../dist/models/upload/upload_CN.md`），抓取不到时再回退到网页渲染抓取。
如果 docdata 发布了新版本目录，可在 `.env` 中设置：

```bash
MODELSCOPE_DOCS_DOCDATA_VERSION=2026-3-17_11-15-CN
```

默认输出目录和状态文件：

- Markdown：`data/raw/`
- 增量状态：`data/crawl_state.json`

### 持续更新

```bash
# 每 3 小时更新一轮
uv run python crawl.py --loop --interval-minutes 180
```

### 重新构建向量索引

```bash
uv run python build.py
```

`build.py` 已支持递归读取目录，`data/raw` 下的分目录 Markdown 会自动入库。

## 环境变量配置

创建 `.env` 文件并配置以下变量：

```bash
# 必填：阿里云 DashScope API Key（LLM + rerank）
DASHSCOPE_API_KEY=your_dashscope_api_key

# 可选：联网搜索
TAVILY_API_KEY=your_tavily_api_key
```

项目启动时会自动加载 `.env`。

## 模型统一配置

项目已将 LLM、Embedding、Rerank 的模型名称统一到一个文件：

- `src/llm/model_config.py`

如需更换模型，仅需修改该文件中的 `MODEL_NAMES`：

- `normal_chat`：路由/重写/打分等非流式调用
- `stream_chat`：最终回答与闲聊流式输出
- `embedding_text`：文本向量化模型（build.py 与文本检索）
- `rerank_text`：文本重排序模型
- `embedding_multimodal`：多模态向量化预留模型
- `rerank_multimodal`：多模态重排序预留模型

### 运行时模型打印

每次运行会在控制台打印真实调用的模型名称（不是配置项 key），便于排查链路问题。当前包含：

- `intent_router`：意图识别模型
- `query_rewrite`：重写模型
- `query_decompose`：查询分解模型
- `doc_grade`：文档打分模型
- `answer_generate` / `chat_generate`：生成模型
- `embedding_text`：文本向量化模型
- `rerank`：重排序模型

## LangSmith 评测

项目新增了模块化评测能力，覆盖三类核心指标：

- 检索质量：`Hit@k`、`Recall@k`、`MRR@k`
- 响应速度：`TTFT`、`Total Latency`、`Chars/sec`
- LLM-as-judge：`relevance`、`groundedness`、`completeness`

### 测试集路径与格式

- 测试集目录：`data/eval/datasets/`
- 示例文件：`data/eval/datasets/sample_rag_eval.jsonl`
- 报告输出：`data/eval/reports/`

每行一个 JSON 样本，必填字段：

1. `case_id`
2. `query`
3. `expected_docids`（非空列表）
4. `difficulty`（`easy|medium|hard`）

### 运行评测

```bash
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10
```

### 上传 LangSmith

```bash
LANGCHAIN_API_KEY=your_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=modelscope-rag-eval

uv run python scripts/run_eval.py \
	--dataset data/eval/datasets/sample_rag_eval.jsonl \
	--upload-langsmith \
	--dataset-name modelscope_rag_eval
```

更完整的数据集构建与 docid 标注说明见：`EVAL_LANGSMITH_GUIDE.md`

## 许可证

Apache License 2.0