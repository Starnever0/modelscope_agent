# LangSmith 评测说明

## 1. 评测内容

本项目固定评测三类指标：

1. 召回质量：Hit@k、Recall@k、MRR@k
2. 响应速度：TTFT、Total Latency、Chars/sec
3. LLM as Judge：relevance、groundedness、completeness、judge_score

## 2. 测试集路径与格式

请将测试集放在以下目录：

- data/eval/datasets/*.jsonl

示例文件：

- data/eval/datasets/sample_rag_eval.jsonl

每行必须是一个 JSON 对象，必填字段：

1. case_id（字符串）
2. query（字符串）
3. expected_docids（非空字符串列表）
4. difficulty（easy/medium/hard）

可选字段：

1. reference_answer（字符串）
2. tags（字符串列表）
3. metadata（对象）

补充字段（按场景使用）：

1. dataset_type：`qa` 或 `feedback`，默认 `qa`
2. bot_answer：反馈数据集中的机器人历史回答
3. user_rating：用户评分（数字）
4. user_feedback：用户文本反馈

## 2.1 三类数据集构造方式

### A) 有标准问答、但不含 docid

适用：你有 `问题 + 标准答案`，但没有可追踪 docid。

构造规则：

1. `expected_docids` 可以留空列表 `[]`
2. 必须提供 `reference_answer`
3. `dataset_type` 使用 `qa`

示例：

{"case_id":"qa_no_docid_001","query":"如何下载模型？","reference_answer":"可使用SDK或CLI下载。","expected_docids":[],"dataset_type":"qa","difficulty":"easy"}

评测行为：

1. 召回指标会自动跳过（因为无 docid）
2. 仍会执行文本相似度与 LLM-as-judge
3. 仍会执行响应速度评测

### B) 反馈数据集（问题/机器人回答/评分/反馈）

适用：你有线上评测反馈数据。

构造规则：

1. `dataset_type` 设为 `feedback`
2. 必填 `bot_answer`
3. 可选 `user_rating`、`user_feedback`
4. `expected_docids` 可为空

示例：

{"case_id":"fb_001","query":"如何部署模型？","bot_answer":"可进入模型页后点击部署。","user_rating":4,"user_feedback":"步骤可以更详细","expected_docids":[],"dataset_type":"feedback","difficulty":"easy"}

评测行为：

1. 默认复用 `bot_answer`，不强制重新生成
2. 输出反馈统计（平均评分、反馈覆盖率）
3. 若有 `reference_answer`，也可同时计算相似度与 judge

### C) 含 docid 的标准评测集

适用：需要完整检索质量评估（Hit/Recall/MRR）。

构造规则：

1. 为每条样本标注 1 到 3 个 `expected_docids`
2. `dataset_type` 使用 `qa`
3. 建议同时提供 `reference_answer`

示例：

{"case_id":"qa_with_docid_001","query":"ModelScope如何下载模型？","reference_answer":"可通过SDK与CLI。","expected_docids":["doc_abcd1234"],"dataset_type":"qa","difficulty":"easy"}

## 3. 如何确定 docid

推荐方式：

1. 在构建切片时直接写入 metadata.docid。
2. docid 规则确定后保持稳定，不要频繁变更。

当前评测回退规则：

1. 文档 metadata 中存在 docid 时，直接使用。
2. 否则用 source_url|chunk_index|page_content 生成稳定哈希 docid。

标注 expected_docids 时，建议先跑一次检索并查看返回文档的 docid 再填写。

补充：如何构造“有 docid”的数据集

1. 先对目标 query 跑检索，拿到候选文档
2. 从候选文档中挑选最相关 1 到 3 条
3. 读取文档 metadata.docid（若存在）
4. 若不存在，使用回退规则生成 docid（脚本内已支持）
5. 把 docid 写入该样本的 expected_docids

## 4. 如何构建新的测试集

1. 从真实用户问题与历史失败案例中抽样。
2. 每条样本标注 1 到 3 个 expected_docids。
3. 控制难度分布，建议 easy:medium:hard = 4:4:2。
4. 在全量评测前先跑 schema 单测校验。

## 4.1 从 CSV/人工表格快速转换

脚本：`scripts/prepare_eval_dataset.py`

1. 反馈集 CSV 转 JSONL：

uv run python scripts/prepare_eval_dataset.py --mode feedback --input your_feedback.csv --output data/eval/datasets/feedback_eval.jsonl

2. 标准问答 CSV 转 JSONL：

uv run python scripts/prepare_eval_dataset.py --mode qa --input your_qa.csv --output data/eval/datasets/qa_eval.jsonl

字段兼容说明：

1. 支持中文列名（问题、答疑机器人回答、用户评分、用户反馈、标准答案）
2. 也支持英文列名（query、bot_answer、user_rating、user_feedback、reference_answer）

## 4.2 自动生成候选 + 人工审核

脚本：`scripts/generate_eval_candidates.py`

用途：

1. 从 FAISS 向量库随机抽取一个或多个文档
2. 自动生成 simple/medium/hard 问题和参考答案
3. 自动写入 source_docid 与 review_status=pending，供人工审核

命令示例：

uv run python scripts/generate_eval_candidates.py --faiss-dir data/faiss_db --sample-size 20 --output data/eval/datasets/auto_candidates.jsonl

人工审核建议流程：

1. 打开 auto_candidates.jsonl
2. 删除不合理样本，修正问题与答案
3. 将 metadata.review_status 从 pending 改为 approved
4. 另存为正式评测集（例如 qa_eval_v2.jsonl）

## 5. 本地运行评测

命令：

uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10

输出报告路径：

- data/eval/reports/eval_report_YYYYmmdd_HHMMSS.json

说明：

1. 数据集中存在 expected_docids 时，自动执行召回评测
2. 没有 expected_docids 时，召回指标自动跳过
3. 只要有 query，就可评估速度与 LLM-as-judge
4. 有 reference_answer 时可计算文本相似度

## 6. 上传到 LangSmith

先设置环境变量：

LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=modelscope-rag-eval

再执行上传命令：

uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --upload-langsmith --dataset-name modelscope_rag_eval

上传内容：

1. 样本输入：query/case_id/tags/difficulty/dataset_type
2. 样本输出：expected_docids/reference_answer/bot_answer/user_rating/user_feedback
3. 评测摘要：retrieval（可选）/latency/text_similarity/judge/feedback（可选）

## 7. 模块结构说明

- src/eval/dataset_io.py：测试集读取与校验
- src/eval/docid.py：docid 生成与提取
- src/eval/retrieval_eval.py：召回类指标计算
- src/eval/latency_eval.py：速度类指标计算
- src/eval/judge_eval.py：LLM as Judge 评估
- src/eval/langsmith_sync.py：LangSmith 数据集与结果同步
- scripts/run_eval.py：评测入口脚本
