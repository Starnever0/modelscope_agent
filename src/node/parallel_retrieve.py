from typing import List
from langchain_core.documents import Document
from src.node.retriever import get_cached_retriever
from src.state.state import RagState
from src.test import timing_decorator


@timing_decorator
def parallel_retrieve_node(state: RagState):
    """
    并行检索节点：针对分解后的多个子查询分别检索，并去重合并结果
    
    工作流程：
    1. 检查是否存在子查询，若无则直接返回已有的单次检索结果
    2. 对每个子查询调用 retriever 获取相关文档
    3. 使用 set 对文档内容去重，避免重复文档
    4. 返回合并后的所有唯一文档列表
    """
    # 从状态中获取分解后的子查询列表
    sub_questions: List[str] = state["sub_questions"]
    
    # 如果没有子查询（分解节点判定为简单查询或异常），直接返回已有检索结果
    if not sub_questions: # 分解异常的兜底
        return {"all_retrieved_docs": state["retrieved_docs"]}

    print(f"🔄 开始并行检索 {len(sub_questions)} 个子查询...")

    # 初始化文档收集列表和去重集合
    all_docs: List[Document] = []
    seen_contents = set()  # 用于记录已见过的文档内容，实现去重

    # 获取缓存的检索器实例（避免重复加载向量库）
    retriever = get_cached_retriever("data/faiss_db")

    # 遍历每个子查询进行检索
    for i, sq in enumerate(sub_questions, 1):
        print(f"   检索子查询 {i}: {sq}")
        docs = retriever.invoke(sq)
        
        # 对检索到的文档进行去重处理
        for doc in docs:
            content_key = doc.page_content.strip()
            # 只添加之前未出现过的文档
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                all_docs.append(doc)

    print(f"✅ 合并完成，共获取 {len(all_docs)} 条唯一文档")

    # 返回去重后的所有文档
    return {"all_retrieved_docs": all_docs}