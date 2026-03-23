"""
生成“真实用户风格”的 RAG 评测集（包含问题 + 参考答案 + docid）。

目标：
1. 模拟真实用户长尾提问分布，而不是纯技术工程化问法。
2. 保证问题单轮可理解、可由给定文档回答。
3. 同时生成可用于评测的 reference_answer。
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
    reference_answer: str
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


def _normalize_query(text: str) -> str:
    q = _repair_mojibake((text or "").strip())
    q = re.sub(r"\s+", " ", q)
    q = q.replace("？？", "？")
    return q


def _normalize_answer(text: str) -> str:
    a = _repair_mojibake((text or "").strip())
    a = re.sub(r"\s+", " ", a)
    return a


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


def _normalize_difficulty(value: str, idx: int, total: int) -> str:
    val = (value or "").strip().lower()
    mapping = {
        "easy": "easy",
        "simple": "easy",
        "medium": "medium",
        "normal": "medium",
        "hard": "hard",
        "complex": "hard",
    }
    if val in mapping:
        return mapping[val]

    # 默认按 50/30/20 分布回退
    if total <= 0:
        return "easy"
    ratio = idx / total
    if ratio <= 0.5:
        return "easy"
    if ratio <= 0.8:
        return "medium"
    return "hard"


def _build_doc_payload(doc, idx: int) -> dict:
    docid = build_docid_from_document(doc, fallback_chunk_index=idx)
    metadata = doc.metadata or {}
    title = _repair_mojibake(
        str(metadata.get("title") or metadata.get("source_file") or "文档主题").strip()
    )
    url = str(metadata.get("source_url") or metadata.get("url") or "").strip()
    snippet = _repair_mojibake((doc.page_content or "").replace("\n", " ").strip()[:320])
    return {
        "docid": docid,
        "title": title or "文档主题",
        "url": url,
        "snippet": snippet,
    }


def _build_generator_chain():
    llm = get_normal_llm_for_scene("eval_candidate_generate")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
你是RAG评测集构造助手，目标是生成可用于单轮问答评测的真实用户问题。

核心目标：
评测 query理解能力、检索能力、多文档聚合能力；不是评测知识难度。

【最重要约束】
所有问题必须：
1. 单轮可理解（self-contained）
2. 必须能被提供文档回答
3. 不能依赖上下文
4. 不能生成无答案问题
5. 不允许生成需要追问的问题
6. 不允许生成指代不清的问题

禁止示例：
- 那个模型怎么训练？
- 那个功能在哪？
- 之前说的部署怎么做？

允许示例：
- ModelScope上的模型一般怎么训练？
- 平台上的模型部署流程是什么？
- 支持哪些模型训练方式？

【真实提问分布（按用户长尾）】
- 功能探索型：40%
- 入门理解型：25%
- 对比选择型：15%
- 任务导向型：10%
- 深度技术型：10%

【难度定义（按RAG检索难度，不是技术深度）】
easy：关键词完整、单文档可回答
medium：任务型，需组合信息，1-2文档
hard：自然长query/场景描述，多跳信息，2-3文档

【文档关联】
- easy -> 1 文档
- medium -> 1-2 文档
- hard -> 2-3 文档

【难度比例】
- easy 约50%
- medium 约30%
- hard 约20%

【答案要求】
1. 生成 reference_answer，必须能从给定文档片段直接支持。
2. 回答简洁、事实化，不编造文档外信息。
3. 若信息在片段里不完整，不要扩写未知细节。

【输出硬约束】
1. 只输出一个 JSON 对象，根节点必须是 {{"items":[...]}}。
2. 所有字符串必须使用英文双引号，不得使用中文引号。
3. 禁止输出 markdown 代码块、解释、备注、前后缀文字。
4. source_docids 只能使用输入 docs_json 中出现过的 docid。

输出结构（示例）：
{{
    "items": [
        {{"difficulty":"easy","query":"问题","reference_answer":"答案","source_docids":["docid_a"]}},
        {{"difficulty":"medium","query":"问题","reference_answer":"答案","source_docids":["docid_a","docid_b"]}},
        {{"difficulty":"hard","query":"问题","reference_answer":"答案","source_docids":["docid_b","docid_c"]}}
    ]
}}
                """.strip(),
            ),
            (
                "human",
                """
基于以下文档主题生成 {target_count} 条问答样本：

{docs_json}

记住：
1. 所有问题必须可以直接由文档回答。
2. 问题风格要符合真实用户，而不是纯工程化问法。
3. 输出必须是严格 JSON。

few-shot 示例（请学习风格，不要照抄）：
输入主题（示意）：
[{{"docid":"doc_demo_download","title":"模型下载","url":"https://modelscope.cn/docs/datasets/download","snippet":"支持 SDK 与命令行下载，提供鉴权与缓存说明"}}]

用户可能的问题：
我想下载xx模型，应该怎么下载？

你应输出（示意）：
{{
    "items": [
        {{
            "difficulty": "easy",
            "query": "我想下载一个模型，通常有哪些下载方式？",
            "reference_answer": "可通过 SDK 或命令行进行下载，下载前需完成鉴权并按文档说明处理本地缓存。",
            "source_docids": ["doc_demo_download"]
        }}
    ]
}}
                """.strip(),
            ),
        ]
    )
    return prompt | llm


def _pick_fallback_query_and_answer(title: str, snippet: str, difficulty: str) -> tuple[str, str]:
    title = title or "该主题"
    if difficulty == "easy":
        return (
            f"{title}主要能做什么？",
            snippet[:120] if snippet else f"可参考文档《{title}》中的功能说明。",
        )
    if difficulty == "medium":
        return (
            f"如果我是新手，使用{title}的大致步骤是什么？",
            snippet[:140] if snippet else f"可按《{title}》文档给出的流程逐步操作。",
        )
    return (
        f"想把{title}用于真实业务场景时，需要重点关注哪些限制或关键步骤？",
        snippet[:160] if snippet else f"可参考《{title}》中的限制条件与关键步骤说明。",
    )


def generate_realistic_qa(
    faiss_dir: str,
    question_count: int,
    output_jsonl: str,
    seed: int = 42,
    docs_per_prompt: int = 8,
    max_questions_per_call: int = 20,
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

    rows: list[dict[str, Any]] = []
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

        items: list[dict[str, Any]] = []
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

        if not items:
            fallback_batches += 1
            for i in range(target_count):
                picked_doc = rnd.choice(batch_docs)
                fallback_difficulty = _normalize_difficulty("", len(rows) + i + 1, question_count)
                query, answer = _pick_fallback_query_and_answer(
                    picked_doc.get("title", ""),
                    picked_doc.get("snippet", ""),
                    fallback_difficulty,
                )
                items.append(
                    {
                        "difficulty": fallback_difficulty,
                        "query": query,
                        "reference_answer": answer,
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

            query = _normalize_query(str(item.get("query") or ""))
            answer = _normalize_answer(str(item.get("reference_answer") or ""))

            if not query:
                query, answer = _pick_fallback_query_and_answer(
                    source_titles[0] if source_titles else "",
                    docid_to_meta[linked_docids[0]].get("snippet", "") if linked_docids else "",
                    difficulty,
                )

            if not answer:
                answer = docid_to_meta[linked_docids[0]].get("snippet", "")[:140] if linked_docids else ""

            key = _query_key(query)
            if key in used_query_keys:
                query = f"{query.rstrip('？')}（样本{row_index}）？"
                key = _query_key(query)

            used_query_keys.add(key)

            rows.append(
                {
                    "case_id": f"real_q_{row_index}",
                    "query": query,
                    "reference_answer": answer,
                    "expected_docids": linked_docids,
                    "difficulty": difficulty,
                    "dataset_type": "qa",
                    "tags": ["auto_generated", "real_user_style", "docid_labeled", "with_reference_answer"],
                    "metadata": {
                        "review_status": "pending",
                        "source_docids": linked_docids,
                        "source_titles": source_titles,
                        "source_urls": source_urls,
                        "embedding_model": get_active_embedding_model_name(),
                        "generation_mode": "llm_realistic_qa",
                        "generation_source": str(item.get("_generation_source") or "llm"),
                    },
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Generated {len(rows)} realistic QA rows at: {out_path}")
    print(f"Batch stats => llm_success: {llm_success_batches}, fallback: {fallback_batches}")


def main():
    parser = argparse.ArgumentParser(description="Generate realistic-user-style QA eval dataset with docid + answers")
    parser.add_argument("--faiss-dir", default="data/faiss_db")
    parser.add_argument("--question-count", type=int, default=60, help="Total number of QA samples to generate")
    parser.add_argument("--docs-per-prompt", type=int, default=8, help="Number of docs included in each LLM prompt")
    parser.add_argument("--max-questions-per-call", type=int, default=20, help="Max samples generated per LLM call")
    parser.add_argument("--output", default="data/eval/datasets/auto_realistic_qa_candidates.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_realistic_qa(
        faiss_dir=args.faiss_dir,
        question_count=args.question_count,
        output_jsonl=args.output,
        seed=args.seed,
        docs_per_prompt=args.docs_per_prompt,
        max_questions_per_call=args.max_questions_per_call,
    )


if __name__ == "__main__":
    main()
