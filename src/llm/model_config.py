import os
from typing import List

from dashscope import TextReRank
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings


# 统一模型名称配置：后续替换模型时只改这里
# MODEL_NAMES = {
#     "normal_chat": "qwen-flash",
#     "stream_chat": "qwen3-max",
#     "embedding": "text-embedding-v4",
#     "rerank": "qwen3-rerank",
# }
MODEL_NAMES = {
    # 当前账号下 qwen3.5-flash 会触发 InvalidParameter(url)，先使用可用模型保障主链路可运行
    "normal_chat": "qwen-turbo",
    "stream_chat": "qwen3-max-2026-01-23",
    # 文本 RAG 默认模型（build.py 索引构建使用文本切片）
    "embedding_text": "text-embedding-v4",
    "rerank_text": "qwen3-rerank",
    # 多模态预留模型（仅用于图文向量化，不用于纯文本向量化）
    "embedding_multimodal": "qwen3-vl-embedding",
    "rerank_multimodal": "qwen3-vl-rerank",
}

_PRINTED_MODEL_USAGE = set()


def _print_model_usage(scene: str, model_name: str):
    key = (scene, model_name)
    if key in _PRINTED_MODEL_USAGE:
        return
    print(f"🧭 [Model] {scene}: {model_name}")
    _PRINTED_MODEL_USAGE.add(key)


def get_normal_llm(scene: str = "normal_chat"):
    llm = ChatTongyi(
        model=MODEL_NAMES["normal_chat"],
        extra_body={"enable_thinking": False},
        temperature=0,
    )
    _print_model_usage(scene, getattr(llm, "model_name", MODEL_NAMES["normal_chat"]))
    return llm


def get_stream_llm(scene: str = "stream_chat"):
    llm = ChatTongyi(
        model=MODEL_NAMES["stream_chat"],
        streaming=True,
    )
    _print_model_usage(scene, getattr(llm, "model_name", MODEL_NAMES["stream_chat"]))
    return llm


def get_embedding_model():
    # 文本向量化固定使用 text embedding 模型。
    model_name = get_active_embedding_model_name()
    _print_model_usage("embedding_text", model_name)

    return DashScopeEmbeddings(
        model=model_name,
    )


def get_active_embedding_model_name() -> str:
    model_name = os.getenv("RAG_EMBEDDING_MODEL", MODEL_NAMES["embedding_text"])
    if any(k in model_name.lower() for k in ["vl", "multimodal", "vision"]):
        raise ValueError(
            "RAG_EMBEDDING_MODEL 必须是文本 embedding 模型。"
            "若需要图文向量化，请使用 get_multimodal_embedding_model_name() 获取多模态模型。"
        )
    return model_name


def get_multimodal_embedding_model_name() -> str:
    return os.getenv("RAG_MULTIMODAL_EMBEDDING_MODEL", MODEL_NAMES["embedding_multimodal"])


def get_active_rerank_model_name() -> str:
    return os.getenv("RAG_RERANK_MODEL", MODEL_NAMES["rerank_text"])


def call_rerank(query: str, documents: List[str], top_n: int = 10):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

    model_name = get_active_rerank_model_name()
    _print_model_usage("rerank", model_name)

    return TextReRank.call(
        model=model_name,
        query=query,
        documents=documents,
        top_n=top_n,
        api_key=api_key,
    )
