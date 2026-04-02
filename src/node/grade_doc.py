from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.llm.provider import get_normal_llm_for_scene
from src.prompt.grade_doc_prompt import grade_doc_system_prompt
from src.test import timing_decorator


class GradeDocuments(BaseModel):
    """文档相关性评估结果"""
    binary_score: Literal["yes", "no"] = Field(
        description="文档是否与用户问题相关？'yes' 表示相关，'no' 表示不相关。"
    )

parser = PydanticOutputParser(pydantic_object=GradeDocuments)


grade_system_prompt = ChatPromptTemplate.from_messages([
    ("system", grade_doc_system_prompt),
    ("user", "【用户查询】：{query} \n\n【检索文档】：{documents}")
]).partial(format_instructions=parser.get_format_instructions())

grade_chain = grade_system_prompt | get_normal_llm_for_scene("doc_grade") | parser


def _build_grade_documents_text(retrieved_docs: list, max_docs: int = 3, max_chars_per_doc: int = 1200) -> str:
    parts: list[str] = []
    for i, doc in enumerate(retrieved_docs[:max_docs], 1):
        page_content = str(getattr(doc, "page_content", "")).strip()
        compact_text = page_content[:max_chars_per_doc]
        source = ""
        metadata = getattr(doc, "metadata", {}) or {}
        if isinstance(metadata, dict):
            source = str(metadata.get("source_url") or metadata.get("source") or "")
        header = f"文档{i}"
        if source:
            header += f"（来源: {source}）"
        parts.append(f"{header}:\n{compact_text}")
    return "\n\n".join(parts)

@timing_decorator
def grade_node(state):
    current_step = state.get("loop_step", 0)
    retrieved_docs = state.get("retrieved_docs", [])

    # 无检索结果时不调用 LLM 评分，直接进入重写/兜底分支。
    if not retrieved_docs:
        if current_step < 1:
            print(f"--- 未检索到文档，进行第 {current_step + 1} 次重写 ---")
            return "rewrite_node"
        print("--- 未检索到文档且达到最大重试次数，进入web ---")
        return "web_node"

    documents_text = _build_grade_documents_text(retrieved_docs)
    score = grade_chain.invoke({
        "query": state["rewritten_query"],
        "documents": documents_text
    })
    print(f"   └─ 🤔 文档质量评估结果: {score.binary_score}")
    if score.binary_score == "no" and current_step < 1:
        print(f"--- 质量不达标，进行第 {current_step + 1} 次重写 ---")
        return "rewrite_node"
    if current_step >= 1:
        print("--- 已达到最大重试次数，进入web ---")
        return "web_node"
    return "generator_node"