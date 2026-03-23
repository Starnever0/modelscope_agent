"""
仅计算检索相关指标的评测脚本
Skip：生成答案、LLM评判、延迟评测
Focus：检索质量指标（Hit@k, Recall@k, MRR@k）

改进：使用 source_urls（已有的元数据）进行基于 URL 的匹配，规避 docid hash 不一致问题
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.eval.dataset_io import load_eval_cases_from_jsonl
from src.node.retriever import get_cached_retriever


def build_retrieve_urls_fn():
    """返回文档 URL 的检索函数"""
    retriever = get_cached_retriever("data/faiss_db")
    
    def retrieve_urls(query: str, k: int):
        docs = retriever.invoke(query) if retriever else []
        urls = []
        for doc in docs[:k]:
            metadata = doc.metadata or {}
            url = metadata.get("source_url") or metadata.get("url") or ""
            if url:
                urls.append(url)
        return urls
    
    return retrieve_urls


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
    parser = argparse.ArgumentParser(description="Run retrieval-only eval with URL-based matching")
    parser.add_argument("--dataset", default="data/eval/datasets/sample_rag_eval.jsonl")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output-dir", default="data/eval/reports")
    args = parser.parse_args()

    cases = load_eval_cases_from_jsonl(args.dataset)
    
    # 验证数据集包含 expected_docids 和 source_urls
    has_docids = any(bool(c.expected_docids) for c in cases)
    if not has_docids:
        print("⚠️  警告: 数据集中没有 expected_docids，无法进行检索评测")
        return
    
    print(f"📊 加载评测数据集: {args.dataset}")
    print(f"   包含 {len(cases)} 个样本")
    
    retrieve_urls_fn = build_retrieve_urls_fn()
    
    print(f"🔍 执行检索评测 (k={args.k})...")
    print(f"   使用基于 URL 的匹配模式（利用现有 source_urls 元数据）")
    
    from src.eval.types import EvalItemResult, EvalResult
    
    items = []
    evaluated_count = 0
    url_match_count = 0
    docid_fallback_count = 0
    
    for case in cases:
        if not case.expected_docids:
            items.append(
                EvalItemResult(
                    case_id=case.case_id,
                    metrics={"hit_at_k": 0.0, "recall_at_k": 0.0, "mrr_at_k": 0.0},
                    extra={"skipped": True, "reason": "missing_expected_docids"},
                )
            )
            continue
        
        # 优先使用 source_urls（已有的元数据）
        metadata = case.metadata or {}
        source_urls = metadata.get("source_urls") or []
        
        if source_urls:
            # 基于 URL 的匹配（推荐）
            url_match_count += 1
            retrieved_urls = retrieve_urls_fn(case.query, args.k)
            expected_set = set(source_urls)
            retrieved_set = set(retrieved_urls[:args.k])
            
            hit = 1.0 if any(u in retrieved_set for u in source_urls) else 0.0
            recall = len(expected_set & retrieved_set) / len(source_urls) if source_urls else 0.0
            
            mrr = 0.0
            for idx, url in enumerate(retrieved_urls[:args.k], start=1):
                if url in expected_set:
                    mrr = 1.0 / idx
                    break
            
            extra_info = {
                "match_method": "url_based",
                "expected_urls": source_urls,
                "retrieved_urls": retrieved_urls[:args.k],
            }
        else:
            # 回退：仅使用 docid 匹配（当没有 source_urls 时）
            docid_fallback_count += 1
            from src.eval.docid import build_docid_from_document
            
            retrieved_docs = get_cached_retriever("data/faiss_db").invoke(case.query) if case.query else []
            retrieved_docids = [
                build_docid_from_document(doc, fallback_chunk_index=idx)
                for idx, doc in enumerate(retrieved_docs[:args.k])
            ]
            
            expected_set = set(case.expected_docids)
            retrieved_set = set(retrieved_docids[:args.k])
            
            hit = 1.0 if any(d in retrieved_set for d in case.expected_docids) else 0.0
            recall = len(expected_set & retrieved_set) / len(case.expected_docids) if case.expected_docids else 0.0
            
            mrr = 0.0
            for idx, docid in enumerate(retrieved_docids[:args.k], start=1):
                if docid in expected_set:
                    mrr = 1.0 / idx
                    break
            
            extra_info = {
                "match_method": "docid_based (fallback)",
                "retrieved_docids": retrieved_docids[:args.k],
            }
        
        metrics = {
            "hit_at_k": hit,
            "recall_at_k": recall,
            "mrr_at_k": mrr,
        }
        evaluated_count += 1
        items.append(
            EvalItemResult(
                case_id=case.case_id,
                metrics=metrics,
                extra=extra_info,
            )
        )
    
    # 生成汇总
    count = max(evaluated_count, 1)
    summary = {
        "hit_at_k": round(sum(i.metrics["hit_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "recall_at_k": round(sum(i.metrics["recall_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "mrr_at_k": round(sum(i.metrics["mrr_at_k"] for i in items if not i.extra.get("skipped")) / count, 6),
        "evaluated_count": float(evaluated_count),
        "skipped_count": float(len(items) - evaluated_count),
        "url_match_count": float(url_match_count),
        "docid_fallback_count": float(docid_fallback_count),
    }
    
    retrieval_result = EvalResult(items=items, summary=summary)
    
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
    print(f"\n📊 匹配方式统计:")
    print(f"   URL 匹配: {url_match_count} 个样本")
    print(f"   Docid 回退: {docid_fallback_count} 个样本")
    print(f"\n📈 检索指标摘要:")
    for metric, value in retrieval_result.summary.items():
        if not metric.endswith("_count"):
            print(f"   {metric}: {value}")


if __name__ == "__main__":
    main()
