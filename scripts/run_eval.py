import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk

from src.eval.answer_eval import evaluate_text_similarity
from src.eval.dataset_io import load_eval_cases_from_jsonl
from src.eval.docid import build_docid_from_document
from src.eval.feedback_eval import evaluate_feedback
from src.eval.judge_eval import build_llm_judge, evaluate_judge
from src.eval.langsmith_sync import upload_cases_to_langsmith, upload_result_summary
from src.eval.latency_eval import evaluate_latency_for_queries
from src.eval.retrieval_eval import evaluate_retrieval
from src.graph import create_graph
from src.node.retriever import get_cached_retriever


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


def build_retrieve_docids_fn():
    retriever = get_cached_retriever("data/faiss_db")

    def retrieve_docids(query: str, k: int):
        docs = retriever.invoke(query) if retriever else []
        ids = []
        for idx, doc in enumerate(docs[:k]):
            ids.append(build_docid_from_document(doc, fallback_chunk_index=idx))
        return ids

    return retrieve_docids


def build_stream_answer_fn(graph):
    def stream_answer(query: str):
        inputs = {"messages": [{"role": "user", "content": query}]}
        config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
        for chunk in graph.stream(inputs, config, stream_mode="messages"):
            if isinstance(chunk[0], AIMessageChunk):
                content = chunk[0].content
                if isinstance(content, str) and content:
                    yield content

    return stream_answer


def collect_answers(cases, stream_answer_fn):
    answers = {}
    for case in cases:
        # 反馈数据集可直接使用历史机器人回答，避免重复生成
        if case.bot_answer:
            answers[case.case_id] = case.bot_answer
        else:
            answers[case.case_id] = "".join(stream_answer_fn(case.query))
    return answers


def should_run_retrieval(cases) -> bool:
    return any(bool(c.expected_docids) for c in cases)


def main():
    parser = argparse.ArgumentParser(description="Run RAG eval with retrieval/latency/judge metrics")
    parser.add_argument("--dataset", default="data/eval/datasets/sample_rag_eval.jsonl")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output-dir", default="data/eval/reports")
    parser.add_argument("--upload-langsmith", action="store_true")
    parser.add_argument("--dataset-name", default="modelscope_rag_eval")
    args = parser.parse_args()

    load_dotenv()

    cases = load_eval_cases_from_jsonl(args.dataset)
    graph = create_graph()
    retrieve_docids_fn = build_retrieve_docids_fn()
    stream_answer_fn = build_stream_answer_fn(graph)

    retrieval_result = evaluate_retrieval(cases, retrieve_docids_fn, k=args.k) if should_run_retrieval(cases) else None
    latency_result = evaluate_latency_for_queries([c.query for c in cases], stream_answer_fn)
    answers_by_case_id = collect_answers(cases, stream_answer_fn)
    similarity_result = evaluate_text_similarity(cases, answers_by_case_id)
    judge_fn = build_llm_judge()
    judge_result = evaluate_judge(cases, answers_by_case_id, judge_fn)
    feedback_result = evaluate_feedback([c for c in cases if c.dataset_type == "feedback"]) if any(c.dataset_type == "feedback" for c in cases) else None

    merged_summary = {
        "latency": latency_result.summary,
        "text_similarity": similarity_result.summary,
        "judge": judge_result.summary,
    }
    if retrieval_result:
        merged_summary["retrieval"] = retrieval_result.summary
    if feedback_result:
        merged_summary["feedback"] = feedback_result.summary

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"eval_report_{ts}.json"
    out_file.write_text(
        json.dumps(
            {
                "dataset": args.dataset,
                "summary": merged_summary,
                "latency": _to_dict(latency_result),
                "text_similarity": _to_dict(similarity_result),
                "judge": _to_dict(judge_result),
                "answers": answers_by_case_id,
                **({"retrieval": _to_dict(retrieval_result)} if retrieval_result else {}),
                **({"feedback": _to_dict(feedback_result)} if feedback_result else {}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.upload_langsmith:
        if not os.getenv("LANGCHAIN_API_KEY"):
            raise RuntimeError("LANGCHAIN_API_KEY is required when --upload-langsmith is enabled")
        upload_cases_to_langsmith(args.dataset_name, cases)
        if retrieval_result:
            upload_result_summary(args.dataset_name, "retrieval", retrieval_result)
        upload_result_summary(args.dataset_name, "latency", latency_result)
        upload_result_summary(args.dataset_name, "text_similarity", similarity_result)
        upload_result_summary(args.dataset_name, "judge", judge_result)
        if feedback_result:
            upload_result_summary(args.dataset_name, "feedback", feedback_result)

    print(f"Eval done. Report: {out_file}")


if __name__ == "__main__":
    main()
