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

## 3. 如何确定 docid

推荐方式：

1. 在构建切片时直接写入 metadata.docid。
2. docid 规则确定后保持稳定，不要频繁变更。

当前评测回退规则：

1. 文档 metadata 中存在 docid 时，直接使用。
2. 否则用 source_url|chunk_index|page_content 生成稳定哈希 docid。

标注 expected_docids 时，建议先跑一次检索并查看返回文档的 docid 再填写。

## 4. 如何构建新的测试集

1. 从真实用户问题与历史失败案例中抽样。
2. 每条样本标注 1 到 3 个 expected_docids。
3. 控制难度分布，建议 easy:medium:hard = 4:4:2。
4. 在全量评测前先跑 schema 单测校验。

## 5. 本地运行评测

命令：

uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10

输出报告路径：

- data/eval/reports/eval_report_YYYYmmdd_HHMMSS.json

## 6. 上传到 LangSmith

先设置环境变量：

LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=modelscope-rag-eval

再执行上传命令：

uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --upload-langsmith --dataset-name modelscope_rag_eval

## 7. 模块结构说明

- src/eval/dataset_io.py：测试集读取与校验
- src/eval/docid.py：docid 生成与提取
- src/eval/retrieval_eval.py：召回类指标计算
- src/eval/latency_eval.py：速度类指标计算
- src/eval/judge_eval.py：LLM as Judge 评估
- src/eval/langsmith_sync.py：LangSmith 数据集与结果同步
- scripts/run_eval.py：评测入口脚本
