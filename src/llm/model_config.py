import os
from typing import List

from dashscope import MultiModalEmbedding, MultiModalEmbeddingItemText, TextReRank
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings


# 统一模型名称配置：后续替换模型时只改这里
# MODEL_NAMES = {
#     "normal_chat": "qwen-flash",
#     "stream_chat": "qwen3-max",
#     "embedding": "text-embedding-v4",
#     "rerank": "qwen3-rerank",
# }
MODEL_NAMES = {
    "normal_chat": "qwen3.5-flash",
    "stream_chat": "qwen3-max-2026-01-23",
    # 文本 RAG 默认模型（build.py 索引构建使用文本切片）
    "embedding_text": "text-embedding-v4",
    "rerank_text": "qwen3-rerank",
    # 多模态预留模型（未来启用图文检索时再切换）
    "embedding_multimodal": "qwen3-vl-embedding",
    "rerank_multimodal": "qwen3-vl-rerank",
}


class DashScopeMultiModalTextEmbeddings(Embeddings):
    """将多模态 embedding 模型适配为文本 embedding 接口。"""

    def __init__(self, model: str, api_key: str, batch_size: int = 16):
        self.model = model
        self.api_key = api_key
        self.batch_size = batch_size

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        items = [MultiModalEmbeddingItemText(text=t, factor=1.0) for t in texts]
        resp = MultiModalEmbedding.call(
            model=self.model,
            input=items,
            api_key=self.api_key,
        )

        if resp.status_code != 200:
            raise ValueError(
                f"status_code: {resp.status_code}\n code: {getattr(resp, 'code', '')}\n message: {getattr(resp, 'message', '')}"
            )

        embeddings = resp.output.get("embeddings", [])
        return [item["embedding"] for item in embeddings]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        cleaned = [t if isinstance(t, str) else str(t) for t in texts]
        for i in range(0, len(cleaned), self.batch_size):
            results.extend(self._embed_batch(cleaned[i : i + self.batch_size]))
        return results

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]

def get_normal_llm():
    return ChatTongyi(
        model=MODEL_NAMES["normal_chat"],
        extra_body={"enable_thinking": False},
        temperature=0,
    )


def get_stream_llm():
    return ChatTongyi(
        model=MODEL_NAMES["stream_chat"],
        streaming=True,
    )


def get_embedding_model():
    # 允许通过环境变量覆盖，默认走文本 embedding，避免 build.py 纯文本向量化报 InvalidParameter(url)
    model_name = get_active_embedding_model_name()

    # 若启用多模态 embedding（例如 qwen3-vl-embedding），使用多模态接口并以 text item 方式调用
    if any(k in model_name.lower() for k in ["vl", "multimodal", "vision"]):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")
        return DashScopeMultiModalTextEmbeddings(model=model_name, api_key=api_key)

    return DashScopeEmbeddings(
        model=model_name,
    )


def get_active_embedding_model_name() -> str:
    return os.getenv("RAG_EMBEDDING_MODEL", MODEL_NAMES["embedding_text"])


def get_active_rerank_model_name() -> str:
    return os.getenv("RAG_RERANK_MODEL", MODEL_NAMES["rerank_text"])


def call_rerank(query: str, documents: List[str], top_n: int = 10):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

    return TextReRank.call(
        model=get_active_rerank_model_name(),
        query=query,
        documents=documents,
        top_n=top_n,
        api_key=api_key,
    )
