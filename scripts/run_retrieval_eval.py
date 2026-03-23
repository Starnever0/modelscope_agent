"""
仅计算检索相关指标的评测脚本
Skip：生成答案、LLM评判、延迟评测
Focus：检索质量指标（Hit@k, Recall@k, MRR@k）
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.eval.dataset_io import load_eval_cases_from_jsonl
from src.eval.docid import build_docid_from_document
from src.eval.retrieval_eval import evaluate_retrieval
from src.node.retriever import get_cached_retriever


def build_retrieve_docids_fn():
    retriever = get_cached_retriever("data/faiss_db")

    def retrieve_docids(query: str, k: int):
        docs = retriever.invoke(query) if retriever else []
        ids = []
        for idx, doc in enumerate(docs[:k]):
            ids.append(build_docid_from_document(doc, fallback_chunk_index=idx))
        return ids

    return retrieve_docids


def _to_dict(result):
    return {
        "summary": result.summary,
        "items": [
            {
                "case_id": i.case_id,
                "metrics": i.metrics,
                "extra": i.extra,
            }
            for i in result.items
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Run retrieval-only eval (Hit@k, Recall@k, MRR@k)")
    parser.add_argument("--dataset", default="data/eval/datasets/sample_rag_eval.jsonl")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output-dir", default="data/eval/reports")
    args = parser.parse_args()

    cases = load_eval_cases_from_jsonl(args.dataset)
    
    # 验证数据集包含 expected_docids
    has_docids = any(bool(c.expected_docids) for c in cases)
    if not has_docids:
        print("⚠️  警告: 数据集中没有 expected_docids，无法进行检索评测")
        return
    
    print(f"📊 加载评测数据集: {args.dataset}")
    print(f"   包含 {len(cases)} 个样本")
    
    retrieve_docids_fn = build_retrieve_docids_fn()
    
    print(f"🔍 执行检索评测 (k={args.k})...")
    retrieval_result = evaluate_retrieval(cases, retrieve_docids_fn, k=args.k)
    
    # 保存报告
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"eval_retrieval_report_{ts}.json"
    
    report = {
        "dataset": args.dataset,
        "k": args.k,
        "summary": retrieval_result.summary,
        "details": _to_dict(retrieval_result),
    }
    
    out_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    print(f"✅ 检索评测完成！报告已保存: {out_file}")
    print(f"\n📈 检索指标摘要:")
    for metric, value in retrieval_result.summary.items():
        print(f"   {metric}: {value}")


if __name__ == "__main__":
    main()
