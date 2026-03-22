import os
from typing import List

from dashscope import TextReRank
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings


# 统一模型名称配置：后续替换模型时只改这里
MODEL_NAMES = {
    "normal_chat": "qwen-flash",
    "stream_chat": "qwen3-max",
    "embedding": "text-embedding-v4",
    "rerank": "qwen3-rerank",
}


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
    return DashScopeEmbeddings(
        model=MODEL_NAMES["embedding"],
    )


def call_rerank(query: str, documents: List[str], top_n: int = 10):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

    return TextReRank.call(
        model=MODEL_NAMES["rerank"],
        query=query,
        documents=documents,
        top_n=top_n,
        api_key=api_key,
    )
