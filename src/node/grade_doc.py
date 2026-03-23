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

@timing_decorator
def grade_node(state):
    current_step = state.get("loop_step", 0)
    score = grade_chain.invoke({
        "query": state["rewritten_query"],
        "documents": state["retrieved_docs"]
    })
    print(f"   └─ 🤔 文档质量评估结果: {score.binary_score}")
    if score.binary_score == "no" and current_step < 1:
        print(f"--- 质量不达标，进行第 {current_step + 1} 次重写 ---")
        return "rewrite_node"
    if current_step >= 1:
        print("--- 已达到最大重试次数，进入web ---")
        return "web_node"
    return "generator_node"