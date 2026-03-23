import argparse
import json
import random
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

from src.eval.docid import build_docid_from_document
from src.llm.model_config import get_active_embedding_model_name, get_embedding_model
from src.llm.provider import get_normal_llm_for_scene


def _load_docs(faiss_dir: str):
    emb = get_embedding_model()
    vector_store = FAISS.load_local(
        folder_path=faiss_dir,
        embeddings=emb,
        allow_dangerous_deserialization=True,
    )
    return list(vector_store.docstore._dict.values())


def _build_generator_chain():
    llm = get_normal_llm_for_scene("eval_candidate_generate")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
你是评测数据集构造助手。
给定文档内容后，请生成 simple/medium/hard 三个难度的问题与参考答案。
返回严格 JSON，结构如下：
{
  "items": [
    {"difficulty":"easy","query":"...","reference_answer":"..."},
    {"difficulty":"medium","query":"...","reference_answer":"..."},
    {"difficulty":"hard","query":"...","reference_answer":"..."}
  ]
}
""".strip(),
            ),
            (
                "human",
                "文档标题: {title}\n文档URL: {url}\n文档内容:\n{content}",
            ),
        ]
    )
    return prompt | llm


def generate_candidates(faiss_dir: str, sample_size: int, output_jsonl: str, seed: int = 42):
    load_dotenv()
    docs = _load_docs(faiss_dir)
    if not docs:
        raise RuntimeError("No documents found in vector store")

    rnd = random.Random(seed)
    picked = rnd.sample(docs, min(sample_size, len(docs)))

    chain = _build_generator_chain()
    out_path = Path(output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, doc in enumerate(picked, start=1):
        docid = build_docid_from_document(doc, fallback_chunk_index=idx)
        title = str(doc.metadata.get("title") or doc.metadata.get("source_file") or "")
        url = str(doc.metadata.get("source_url") or doc.metadata.get("url") or "")
        content = (doc.page_content or "")[:2000]

        resp = chain.invoke({"title": title, "url": url, "content": content})
        text = getattr(resp, "content", "")
        try:
            parsed = json.loads(text)
            items = parsed.get("items", [])
        except Exception:
            # 失败时保底输出一条，人工后续改写
            items = [
                {
                    "difficulty": "easy",
                    "query": f"{title} 是什么？",
                    "reference_answer": content[:200],
                }
            ]

        for n, item in enumerate(items, start=1):
            rows.append(
                {
                    "case_id": f"auto_{idx}_{n}",
                    "query": str(item.get("query", "")).strip(),
                    "reference_answer": str(item.get("reference_answer", "")).strip(),
                    "expected_docids": [docid],
                    "difficulty": str(item.get("difficulty", "easy")).lower(),
                    "dataset_type": "qa",
                    "tags": ["auto_generated", "need_human_review"],
                    "metadata": {
                        "review_status": "pending",
                        "source_docid": docid,
                        "source_url": url,
                        "source_title": title,
                        "embedding_model": get_active_embedding_model_name(),
                    },
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Generated {len(rows)} candidate rows at: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate eval dataset candidates from random documents")
    parser.add_argument("--faiss-dir", default="data/faiss_db")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--output", default="data/eval/datasets/auto_candidates.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_candidates(
        faiss_dir=args.faiss_dir,
        sample_size=args.sample_size,
        output_jsonl=args.output,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
