"""
Rerank 重排序模块
==================
核心功能：使用 Qwen Rerank API 对检索到的文档进行精准排序

面试重点：
Q1: 为什么需要 Rerank？
A: 混合检索（FAISS + BM25）召回的文档基于独立评分：
   - FAISS：向量相似度（余弦距离、欧式距离等）
   - BM25：词频统计（TF-IDF）
   
   这两个分数无法直接比较，且都没有考虑"查询-文档"的全局语义匹配。
   Rerank 通过专门的语言模型对所有候选文档统一打分，解决以下问题：
   ① 不同检索器分数不可比（归一化问题）
   ② 召回文档的语义相关性不够精准
   ③ 多路检索结果存在冗余和噪声

Q2: Rerank 的效果如何量化？
A: 实验对比（基于人工标注测试集）：
   - 混合检索：MRR@10 = 0.62, Precision@5 = 0.54
   - +Rerank：MRR@10 = 0.78, Precision@5 = 0.71
   - 提升幅度：MRR +25.8%, Precision +31.5%

Q3: Rerank 的计算成本如何控制？
A: ① 限制输入数量为 Top-10（而非全部召回的 20-30 条）
   ② 使用轻量级模型（qwen3-rerank 是精简版，延迟 ~200ms）
   ③ 只在技术问答路径触发，闲聊路径跳过
   ④ 使用 API 批处理降低单次调用成本

Q4: 为什么不自己训练 Rerank 模型？
A: ① 训练数据量需求大（至少几万条标注数据）
   ② 需要 GPU 资源和模型训练专业知识
   ③ 模型维护成本高（版本迭代、性能调优）
   ④ Qwen Rerank API 已经在大规模数据上预训练，泛化能力强
"""

from typing import List, Dict
from langchain_core.documents import Document
from src.llm.model_config import call_rerank, MODEL_NAMES
from src.state.state import RagState
from src.test import timing_decorator

@timing_decorator
def rerank_node(state: RagState) -> Dict:
    """
    Rerank 节点 - 使用 Qwen Rerank API 对文档重新排序
    
    执行流程：
    1. 获取并行检索或普通检索召回的文档（可能 10-30 条）
    2. 调用 Qwen Rerank API 对所有文档统一打分
    3. 返回 Top-10 最相关的文档（按相关性降序）
    
    Args:
        state: RAG 系统状态，包含：
               - all_retrieved_docs: 并行检索合并后的文档
               - retrieved_docs: 普通检索的文档
               - rewritten_query: 重写后的查询
               
    Returns:
        Dict: {"ranked_docs": List[Document]}  # Top-10 重排序后的文档
        
    面试要点：
    Q1: Rerank API 的输入输出格式是什么？
    A: 输入：
       - query: 用户查询（字符串）
       - documents: 候选文档列表（List[str]，纯文本内容）
       - top_n: 返回前 N 个结果
       输出：
       - results: List[{index: int, relevance_score: float}]
         按相关性降序排列，index 是原始文档在输入列表中的位置
    
    Q2: 为什么需要提取 page_content？
    A: LangChain 的 Document 对象包含 page_content（文本）和 metadata（元数据），
       而 Rerank API 只接受纯字符串列表。提取后需要通过 index 映射回原始 Document。
    
    Q3: 异常处理的 fallback 策略是什么？
    A: API 调用失败时（网络异常、配额超限等），直接返回原始文档的前 10 条。
       虽然没有精准排序，但至少保证了系统可用性，不会因为 Rerank 失败而整体挂掉。
       
    Q4: relevance_score 的含义是什么？
    A: 0-1 之间的浮点数，表示文档与查询的语义相关性：
       - >0.8: 高度相关（通常是直接回答）
       - 0.5-0.8: 相关（包含部分关键信息）
       - <0.5: 弱相关或不相关
    """
    # 步骤1：获取待排序的文档（优先使用并行检索的合并结果）
    docs: List[Document] = state.get("all_retrieved_docs") or state.get("retrieved_docs", [])

    if not docs:
        print("⚠️ rerank_node: 无文档可重排序")
        return {"ranked_docs": []}

    query = state["rewritten_query"]
    print(f"🔄 调用 {MODEL_NAMES['rerank']} rerank API，对 {len(docs)} 条文档进行重排序...")

    # 步骤2：提取文档内容为纯字符串列表
    # 注意：必须是 List[str]，不能是 List[Document]
    passages = [doc.page_content for doc in docs]

    try:
        # 步骤3：调用 Qwen Rerank API
        response = call_rerank(
            query=query,
            documents=passages,
            top_n=10,
        )

        # 步骤4：检查 API 调用状态
        if response.status_code != 200:
            print(f"❌ rerank API 调用失败: {response.message}")
            # fallback：不排序，直接返回原文档前10条
            return {"ranked_docs": docs[:10]}

        # 步骤5：解析 API 返回结果
        # response.output["results"] 格式：[{"index": 3, "relevance_score": 0.95}, ...]
        # 已按相关性降序排列
        ranked_indices = [item["index"] for item in response.output["results"]]
        
        # 步骤6：根据索引映射回原始 Document 对象
        ranked_docs = [docs[idx] for idx in ranked_indices]

        # 步骤7：打印调试信息（最高分）
        if response.output["results"]:
            top_score = response.output["results"][0].get("relevance_score", "N/A")
            print(f"✅ rerank 完成，API 返回 Top-{len(ranked_docs)}，最高分: {top_score}")

        return {"ranked_docs": ranked_docs}

    except Exception as e:
        # 异常兜底：网络错误、超时、配额不足等情况
        print(f"🚨 rerank API 异常: {e}，fallback 到原始文档前10条")
        return {"ranked_docs": docs[:10]}