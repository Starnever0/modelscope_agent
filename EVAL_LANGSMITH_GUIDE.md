# LangSmith Evaluation Guide

## 1. What is evaluated

This project evaluates three categories:

1. Retrieval quality: `Hit@k`, `Recall@k`, `MRR@k`
2. Response speed: `TTFT`, `Total Latency`, `Chars/sec`
3. LLM-as-judge: `relevance`, `groundedness`, `completeness`, `judge_score`

## 2. Dataset path and format

Store datasets under:

- `data/eval/datasets/*.jsonl`

Example file:

- `data/eval/datasets/sample_rag_eval.jsonl`

Each line must be a JSON object with required fields:

1. `case_id` (string)
2. `query` (string)
3. `expected_docids` (non-empty list of string)
4. `difficulty` (`easy|medium|hard`)

Optional fields:

1. `reference_answer` (string)
2. `tags` (string list)
3. `metadata` (object)

## 3. How to determine docid

Preferred approach:

1. Persist `metadata.docid` during build/chunking.
2. Keep the same docid generation rule over time.

Current fallback rule in eval:

1. If document metadata contains `docid`, use it directly.
2. Else generate stable hash from `source_url|chunk_index|page_content`.

You can inspect current retrieved docs and fill `expected_docids` accordingly.

## 4. Build a new test set

1. Start from real user queries and historical failures.
2. Label 1-3 expected docids per query.
3. Balance difficulty ratio (recommended: `easy:medium:hard = 4:4:2`).
4. Run schema validation via unit tests before full eval.

## 5. Run local eval

```bash
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --k 10
```

Output report will be written to:

- `data/eval/reports/eval_report_YYYYmmdd_HHMMSS.json`

## 6. Upload to LangSmith

Set env vars:

```bash
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=modelscope-rag-eval
```

Run with upload:

```bash
uv run python scripts/run_eval.py --dataset data/eval/datasets/sample_rag_eval.jsonl --upload-langsmith --dataset-name modelscope_rag_eval
```

## 7. Modular code map

- `src/eval/dataset_io.py`: dataset loading and validation
- `src/eval/docid.py`: docid generation and extraction
- `src/eval/retrieval_eval.py`: retrieval metrics
- `src/eval/latency_eval.py`: latency metrics
- `src/eval/judge_eval.py`: LLM-as-judge metrics
- `src/eval/langsmith_sync.py`: LangSmith dataset/result sync
- `scripts/run_eval.py`: evaluation entrypoint
