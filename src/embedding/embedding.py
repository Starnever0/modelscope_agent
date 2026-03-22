import os

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import OpenAIEmbeddings

# 阿里云 DashScope 提供的文本嵌入服务的一个版本
def get_embedding():
    return DashScopeEmbeddings(
        model="text-embedding-v4",
    )

# def get_embedding():
#     return OpenAIEmbeddings(
#         base_url='https://ms-ens-2899801d-10ec.api-inference.modelscope.cn/v1',
#         api_key='ms-ff2970ce-0322-4605-a7a7-cb910d8c6122',
#         model='Qwen/Qwen3-Embedding-4B'
#     )
