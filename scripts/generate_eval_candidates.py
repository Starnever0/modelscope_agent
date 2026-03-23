"""
自动生成评测候选集的脚本：
从 FAISS 向量数据库抽取文档，分批提供文档主题给 LLM 生成“仅问题+docid”的评测样本，
不生成参考答案以减少模型调用成本。
"""
import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.eval.docid import build_docid_from_document
from src.llm.model_config import get_active_embedding_model_name, get_embedding_model
from src.llm.provider import get_normal_llm_for_scene


class GeneratedItem(BaseModel):
    difficulty: str = "easy"
    query: str
    source_docids: list[str] = Field(default_factory=list)


class GeneratedPayload(BaseModel):
    items: list[GeneratedItem] = Field(default_factory=list)


def _repair_mojibake(text: str) -> str:
    if not text:
        return ""
    try:
        repaired = text.encode("gbk").decode("utf-8")
    except Exception:
        return text
    return repaired if repaired else text


def _strip_wrappers(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _extract_json_object(text: str) -> dict:
    cleaned = _strip_wrappers(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("no json object found")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("json root is not object")
    return parsed


def _validate_payload_items(raw: dict) -> list[dict]:
    try:
        payload = GeneratedPayload.model_validate(raw)
    except AttributeError:
        payload = GeneratedPayload.parse_obj(raw)

    validated = []
    for item in payload.items:
        try:
            obj = item.model_dump()
        except AttributeError:
            obj = item.dict()
        validated.append(obj)
    return validated


def _is_generic_title(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return True
    generic = {
        "untitled",
        "模型概览",
        "概览",
        "介绍",
    }
    return t in generic


def _title_from_url(url: str) -> str:
    if not url:
        return ""
    part = url.rstrip("/").split("/")[-1]
    part = part.replace("-", " ").replace("_", " ").strip()
    return part[:40]


def _normalize_title(title: str, url: str) -> str:
    clean_title = _repair_mojibake((title or "").strip())
    if _is_generic_title(clean_title):
        candidate = _title_from_url(url)
        if candidate:
            return candidate
    return clean_title or "文档主题"


def _normalize_query(text: str) -> str:
    q = _repair_mojibake((text or "").strip())
    q = re.sub(r"\s+", " ", q)
    q = q.replace("？？", "？")
    return q


def _query_key(query: str) -> str:
    key = re.sub(r"\s+", "", (query or "").lower())
    key = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", key)
    return key


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
输入是一组文档主题列表，请你生成从 easy 到 hard 的评测问题，问题要完美符合真实使用场景：
魔搭社区使用者想要向答疑助手询问一些与魔搭社区平台有关的使用问题或者一些相关的技术问题。

要求：
1. 只生成问题，不要生成答案。
2. 问题要自然、可用于真实检索场景。
3. 允许单个问题关联 1 到 3 个文档。
4. 输出严格 JSON，不要输出额外文本。
5. 避免使用“主要介绍了什么”“如何快速理解”这类空泛问法。
6. 问题应包含明确任务意图，例如配置、排障、对比、迁移、优化、选型、限制条件。

输出结构：
{{
    "items": [
        {{"difficulty":"easy","query":"...","source_docids":["docid_a"]}},
        {{"difficulty":"medium","query":"...","source_docids":["docid_a","docid_b"]}},
        {{"difficulty":"hard","query":"...","source_docids":["docid_b","docid_c"]}}
    ]
}}
""".strip(),
            ),
            (
                "human",
                "请基于以下文档主题生成 {target_count} 条问题：\n{docs_json}",
            ),
        ]
    )
    return prompt | llm


def _normalize_difficulty(value: str, idx: int, total: int) -> str:
    val = (value or "").strip().lower()
    mapping = {
        "simple": "easy",
        "easy": "easy",
        "medium": "medium",
        "normal": "medium",
        "hard": "hard",
        "complex": "hard",
    }
    if val in mapping:
        return mapping[val]

    if total <= 0:
        return "easy"
    ratio = idx / total
    if ratio < 0.4:
        return "easy"
    if ratio < 0.8:
        return "medium"
    return "hard"


def _pick_fallback_query(title: str, difficulty: str, rnd: random.Random) -> str:
    title = _repair_mojibake(title or "该文档")
    templates = {
        "easy": [
            "在 {title} 场景下，完成基础配置需要哪些前置条件？",
            "如果第一次使用 {title}，最小可运行流程应该怎么走？",
        ],
        "medium": [
            "基于 {title} 实施时，常见报错的定位与修复步骤是什么？",
            "把 {title} 接入现有系统时，接口和数据流应如何设计？",
        ],
        "hard": [
            "在高并发与高准确率并存的条件下，{title} 的优化策略应如何取舍？",
            "围绕 {title} 做生产级架构时，稳定性与成本该如何平衡？",
        ],
    }
    return rnd.choice(templates.get(difficulty, templates["easy"])).format(title=title)


def _diversify_duplicate_query(query: str, title: str, difficulty: str, idx: int) -> str:
    q = query.rstrip("？")
    suffixes = {
        "easy": [
            f"请给出一步步操作清单（场景{idx}）？",
            f"按新手视角说明关键步骤（样本{idx}）？",
        ],
        "medium": [
            f"请补充失败重试与回滚策略（场景{idx}）？",
            f"若与现有模块集成，边界条件如何定义（样本{idx}）？",
        ],
        "hard": [
            f"请给出性能、成本、可维护性的权衡方案（场景{idx}）？",
            f"如果跨团队落地，治理与监控方案如何设计（样本{idx}）？",
        ],
    }
    tail = suffixes.get(difficulty, suffixes["easy"])[idx % 2]
    return f"{q}，针对“{title}”{tail}"


def _build_doc_payload(doc, idx: int) -> dict:
    docid = build_docid_from_document(doc, fallback_chunk_index=idx)
    title = _normalize_title(
        str(doc.metadata.get("title") or doc.metadata.get("source_file") or "").strip(),
        str(doc.metadata.get("source_url") or doc.metadata.get("url") or "").strip(),
    )
    url = str(doc.metadata.get("source_url") or doc.metadata.get("url") or "").strip()
    snippet = _repair_mojibake((doc.page_content or "").replace("\n", " ").strip()[:280])
    return {
        "docid": docid,
        "title": title,
        "url": url,
        "snippet": snippet,
    }


def generate_candidates(
    faiss_dir: str,
    question_count: int,
    output_jsonl: str,
    seed: int = 42,
    docs_per_prompt: int = 5,
    max_questions_per_call: int = 30,
):
    load_dotenv()
    docs = _load_docs(faiss_dir)
    if not docs:
        raise RuntimeError("No documents found in vector store")
    if question_count <= 0:
        raise ValueError("question_count must be > 0")
    if docs_per_prompt <= 0:
        raise ValueError("docs_per_prompt must be > 0")
    if max_questions_per_call <= 0:
        raise ValueError("max_questions_per_call must be > 0")

    rnd = random.Random(seed)
    doc_indexes = list(range(len(docs)))
    rnd.shuffle(doc_indexes)
    chain = _build_generator_chain()

    out_path = Path(output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    used_query_keys = set()
    llm_success_batches = 0
    fallback_batches = 0
    cursor = 0
    while len(rows) < question_count:
        remain = question_count - len(rows)
        target_count = min(max_questions_per_call, remain)

        batch_docs = []
        for _ in range(docs_per_prompt):
            doc = docs[doc_indexes[cursor % len(doc_indexes)]]
            cursor += 1
            batch_docs.append(_build_doc_payload(doc, cursor))

        batch_docids = {d["docid"] for d in batch_docs}
        docid_to_meta = {d["docid"]: d for d in batch_docs}

        items = []
        for _ in range(2):
            try:
                resp = chain.invoke(
                    {
                        "target_count": target_count,
                        "docs_json": json.dumps(batch_docs, ensure_ascii=False),
                    }
                )
                text = getattr(resp, "content", "")
                parsed = _extract_json_object(text)
                items = _validate_payload_items(parsed)
                if items:
                    llm_success_batches += 1
                    break
            except BaseException as exc:
                print(f"[warn] LLM generation failed for one batch: {exc}")

        # 兜底：当 LLM 输出不可解析时，至少按模板产出当前批次目标条数。
        if not items:
            fallback_batches += 1
            for i in range(target_count):
                picked_doc = rnd.choice(batch_docs)
                fallback_difficulty = _normalize_difficulty("", len(rows) + i + 1, question_count)
                items.append(
                    {
                        "difficulty": fallback_difficulty,
                        "query": _pick_fallback_query(picked_doc.get("title", ""), fallback_difficulty, rnd),
                        "source_docids": [picked_doc["docid"]],
                        "_generation_source": "fallback",
                    }
                )

        for item in items:
            if len(rows) >= question_count:
                break

            raw_docids = item.get("source_docids") or []
            if isinstance(raw_docids, str):
                raw_docids = [raw_docids]
            linked_docids = [x for x in raw_docids if isinstance(x, str) and x in batch_docids]
            if not linked_docids:
                linked_docids = [rnd.choice(batch_docs)["docid"]]

            linked_docids = linked_docids[:3]
            source_titles = [_repair_mojibake(docid_to_meta[d].get("title", "")) for d in linked_docids]
            source_urls = [docid_to_meta[d].get("url", "") for d in linked_docids]

            row_index = len(rows) + 1
            difficulty = _normalize_difficulty(str(item.get("difficulty", "")), row_index, question_count)
            query = _repair_mojibake(str(item.get("query") or "").strip())
            if not query:
                query = _pick_fallback_query(source_titles[0] if source_titles else "", difficulty, rnd)

            query = _normalize_query(query)
            if any(x in query for x in ["主要介绍了什么", "如何快速理解"]):
                query = _pick_fallback_query(source_titles[0] if source_titles else "", difficulty, rnd)

            key = _query_key(query)
            if key in used_query_keys:
                query = _diversify_duplicate_query(
                    query=query,
                    title=source_titles[0] if source_titles else "文档主题",
                    difficulty=difficulty,
                    idx=row_index,
                )
                key = _query_key(query)

            used_query_keys.add(key)

            rows.append(
                {
                    "case_id": f"auto_q_{row_index}",
                    "query": query,
                    "expected_docids": linked_docids,
                    "difficulty": difficulty,
                    "dataset_type": "qa",
                    "tags": ["auto_generated", "need_human_review", "docid_labeled", "question_only"],
                    "metadata": {
                        "review_status": "pending",
                        "source_docids": linked_docids,
                        "source_titles": source_titles,
                        "source_urls": source_urls,
                        "embedding_model": get_active_embedding_model_name(),
                        "generation_mode": "llm_question_only",
                        "generation_source": str(item.get("_generation_source") or "llm"),
                    },
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Generated {len(rows)} candidate rows at: {out_path}")
    print(f"Batch stats => llm_success: {llm_success_batches}, fallback: {fallback_batches}")


def main():
    parser = argparse.ArgumentParser(description="Generate LLM-based question-only eval dataset with docid")
    parser.add_argument("--faiss-dir", default="data/faiss_db")
    parser.add_argument("--question-count", type=int, default=60, help="Total number of questions to generate")
    parser.add_argument("--docs-per-prompt", type=int, default=5, help="Number of docs included in each LLM prompt")
    parser.add_argument("--max-questions-per-call", type=int, default=30, help="Max questions generated per LLM call")
    parser.add_argument("--output", default="data/eval/datasets/auto_candidates.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_candidates(
        faiss_dir=args.faiss_dir,
        question_count=args.question_count,
        output_jsonl=args.output,
        seed=args.seed,
        docs_per_prompt=args.docs_per_prompt,
        max_questions_per_call=args.max_questions_per_call,
    )


if __name__ == "__main__":
    main()
