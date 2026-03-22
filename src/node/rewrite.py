from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.llm.provider import get_normal_llm
from src.prompt.rewrite_prompt import rewrite_system_prompt
from src.test import timing_decorator


class RedraftQuery(BaseModel):
    """查询重写结果"""
    revised_query: str = Field(
        description="重写后的优化搜索语句。应包含核心技术栈名词和具体问题动作。"
    )
parser = PydanticOutputParser(pydantic_object=RedraftQuery)

system_prompt = ChatPromptTemplate.from_messages([
    ("system", rewrite_system_prompt),
    ("user", "【原始查询】：{query} \n\n【重写要求】：请生成一个更有利于检索到技术文档的关键词组合，保持简洁精准。")
]).partial(format_instructions=parser.get_format_instructions())

rewrite_chain = system_prompt | get_normal_llm() | parser
@timing_decorator
def rewrite_node(state):
    try:
        print("🤔 重写查询...")
        res = rewrite_chain.invoke({
            "query": state["rewritten_query"]
        })
        print(f"   └─ 🤔 重写结果：{res.revised_query}")
        return {"rewritten_query": res.revised_query, "loop_step": 1}
    except Exception as e:
        print(f"   └─ 🤔 重写失败：{e}")
        return {"rewritten_query": state["rewritten_query"], "loop_step": 1}