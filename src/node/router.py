"""
Router 路由模块
================
核心功能：意图识别 + 指代消歧（多轮对话上下文理解）

面试重点：
Q1: 为什么需要 Router 节点？
A: 实现两个关键功能：
   ① 意图路由：区分"闲聊"和"技术问答"，避免简单问题浪费检索资源
   ② 指代消歧：处理多轮对话中的模糊指代（如"它"、"这个"）
   
   用户体验：不需要每次都输入完整问题，可以自然地进行多轮追问

Q2: 指代消歧的挑战是什么？
A: 典型场景：
   用户："如何部署 Qwen2.5？"
   助手："可以通过 ModelScope SDK..."
   用户："它支持多卡吗？" ← "它"指代不明
   
   如果直接用"它支持多卡吗"去检索，会因为缺少主语而召回大量无关文档。
   Router 通过分析对话历史，将查询补全为"Qwen2.5 支持多卡吗？"

Q3: 如何实现指代消歧？
A: 使用 LLM 分析对话历史：
   输入：历史消息列表 + 当前查询
   输出：独立的、语义完整的查询（不需要看历史也能理解）
   
   关键设计：
   - 只补充必要实体，不添加额外修饰（保持用户原意）
   - 如果没有明显指代，直接返回原句（避免过度处理）

Q4: 为什么要区分 chat 和 docs？
A: ① 节省成本：闲聊不需要检索，直接用 LLM 生成
   ② 优化体验：问候语不需要等待检索延迟（<1s vs 3s）
   ③ 提高准确性：技术问题基于知识库回答，避免幻觉
"""

from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.llm.provider import get_normal_llm_for_scene
from src.prompt.router_prompt import router_system_prompt
from src.test import timing_decorator


class RouterOutput(BaseModel):
    """
    Router 节点的输出格式（使用 Pydantic 实现结构化输出）
    
    面试要点：
    Q: 为什么使用 Pydantic 而不是直接解析字符串？
    A: ① 类型安全：自动验证输出格式，避免解析错误
       ② 自动补全：IDE 可以提供字段提示和类型检查
       ③ 文档生成：description 字段可以自动生成 API 文档
       ④ 与 LLM 集成：通过 PydanticOutputParser 将格式要求注入到提示词中
    """
    standalone_query: str = Field(
        ...,
        description="处理后的独立查询语句。处理规则（严格按优先级执行）：\n"
                    "1. 如果用户当前输入中存在明显的指代模糊（如 '它'、'这个'、'那个'、'该框架'、'上一个'、'其他方式'、'除了这个还有吗'、'怎么用' 等），\n"
                    "   必须基于对话历史补全缺失的主语/宾语/核心实体，形成一个语义完整的自然问句。\n"
                    "   - 补全时优先保持用户原句的结构和语气\n"
                    "   - 只补充必要实体，不添加额外修饰、不优化关键词、不拆解问题\n"
                    "   - 目标：让结果成为一个不需要看历史也能理解的完整问题\n"
                    "2. 如果没有明显的指代模糊，直接使用用户最后一条消息的原句，不做任何改动。\n"
                    "\n"
                    "示例：\n"
                    "   - 当前输入：'还有其他方式吗'，历史提到 '如何快速部署qwen' → 输出：'qwen快速部署还有其他方式吗'\n"
                    "   - 当前输入：'它怎么训练？'，历史提到 'Qwen2' → 输出：'Qwen2怎么训练？'\n"
                    "   - 当前输入：'这个参数怎么设置'，历史提到 'SWIFT的lora_target' → 输出：'SWIFT的lora_target参数怎么设置'\n"
                    "   - 当前输入：'多卡训练支持吗'，历史无明确指代但上下文是SWIFT → 输出：'SWIFT多卡训练支持吗'\n"
                    "   - 当前输入：'你好' → 输出：'你好'（无改动）"
    )
    datasource: Literal["docs", "chat"] = Field(
        ...,
        description="路由决策：chat (问候、闲聊、通用代码编写、报错堆栈诊断); docs (魔搭社区平台操作、SWIFT框架使用、模型下载部署、社区活动、官方文档查询)"
    )
# ============ 初始化 LLM 链 ============

# 解析器：将 LLM 输出解析为 RouterOutput 对象
parser = PydanticOutputParser(pydantic_object=RouterOutput)

# 提示词模板：包含系统提示 + 对话历史占位符
route_prompt = ChatPromptTemplate.from_messages([
    ("system", router_system_prompt),  # 系统角色定义和任务描述
    ("placeholder", "{messages}"),     # 对话历史占位符（自动填充）
]).partial(format_instructions=parser.get_format_instructions())  # 注入输出格式要求

# 获取 LLM 实例（通常是 Qwen 系列模型）
llm = get_normal_llm_for_scene("intent_router")

# 构建 LangChain 链：提示词 → LLM → 解析器
# 面试要点：这是 LangChain 的 LCEL（LangChain Expression Language）语法
# 优势：① 链式调用更简洁 ② 支持流式输出 ③ 自动错误传递
router_chain = route_prompt | llm | parser


@timing_decorator
def router_node(state):
    """
    Router 节点 - LangGraph 工作流的入口节点
    
    功能：
    1. 分析用户意图（闲聊 vs 技术问答）
    2. 处理多轮对话中的指代消歧
    3. 生成独立的、语义完整的查询
    
    Args:
        state: RAG 系统状态，包含：
               - messages: 对话历史（List[BaseMessage]）
               
    Returns:
        Dict: {
            "rewritten_query": str,     # 重写后的查询
            "datasource": "chat"|"docs" # 路由决策
        }
        
    执行流程：
    1. 将对话历史传递给 LLM 链
    2. LLM 分析用户意图并补全指代
    3. 返回独立查询和路由决策
    """
    print("🤔 正在分析用户意图...")
    try:
        # 调用 LLM 链：提示词 → LLM → 解析器
        analysis = router_chain.invoke({"messages": state["messages"]})

        # 打印调试信息
        print(f"   └─ 🧐 意图: {analysis.datasource}")
        print(f"   └─ 📝 重写: {analysis.standalone_query}")

        # 返回路由结果
        return {
            "rewritten_query": analysis.standalone_query,
            "datasource": analysis.datasource
        }

    except Exception as e:
        # 【兜底策略】异常处理：解析失败时的降级方案
        print(f"🚨 路由解析失败: {e}")
        # 【兜底策略】如果解析挂了，默认回退到 docs
        last_msg = state["messages"][-1].content
        print(f"   └─ ⚠️ 降级到原始查询: {last_msg}")
        return {
            "rewritten_query": last_msg,    # 使用原始查询
            "datasource": "docs"            # 默认路由到技术问答路径
        }