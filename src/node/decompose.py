from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from src.llm.provider import get_normal_llm_for_scene
from src.prompt.decompose_prompt import decompose_system_prompt
from src.state.state import RagState
from src.test import timing_decorator


class DecompositionOutput(BaseModel):
    """查询分解结果"""
    is_complex: bool = Field(description="是否为复杂查询（包含多个独立子问题）")
    sub_questions: List[str] = Field(description="如果复杂，则分解为多个独立的子查询；否则为空列表")


# 初始化解析器和链
parser = PydanticOutputParser(pydantic_object=DecompositionOutput)

decompose_prompt = ChatPromptTemplate.from_messages([
    ("system", decompose_system_prompt),
    ("human", "{query}")
]).partial(format_instructions=parser.get_format_instructions())

llm = get_normal_llm_for_scene("query_decompose")
decompose_chain = decompose_prompt | llm | parser

@timing_decorator
def decompose_query_node(state: RagState):
    query = state["rewritten_query"] # 这里的重写query只是进行了指代消解而不是我们的重写节点
    print("🔍 正在分析查询复杂度...")

    try:
        result = decompose_chain.invoke({"query": query})
        print(f" └─ 复杂查询: {result.is_complex}")
        if result.is_complex:
            print(f" └─ 分解为 {len(result.sub_questions)} 个子查询:")
            for i, sq in enumerate(result.sub_questions, 1):
                print(f"     {i}. {sq}")

        return {
            "sub_questions": result.sub_questions if result.is_complex else None,
            "all_retrieved_docs": None  # 初始化
        }
    except Exception as e: # 模型如果没有严格返回json，也会报错
        print(f"⚠️ 查询分解失败: {e}，默认按简单查询处理")
        return {
            "sub_questions": None,
            "all_retrieved_docs": None
        }